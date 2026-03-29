"""meal_qr_terminals(통합 행) → meal_printer_terminals / meal_qlight_terminals 분리. 1회성 이행."""
import logging
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_split_legacy_terminals_if_needed(db: Session) -> None:
    from app.models.models import (
        MealLog,
        MealPrinterTerminal,
        MealQlightTerminal,
        MealQrTerminal,
    )

    n_old = db.execute(select(func.count()).select_from(MealQrTerminal)).scalar_one()
    if int(n_old) == 0:
        return

    logger.info("split_legacy_terminals: migrating %s meal_qr_terminals rows", n_old)

    for log in db.scalars(select(MealLog).where(MealLog.qr_terminal_id.isnot(None))):
        t = db.get(MealQrTerminal, log.qr_terminal_id)
        if t is not None:
            log.qr_auth_id = int(t.qr_auth_id)

    for t in db.scalars(select(MealQrTerminal)).all():
        if t.printer_enabled or (t.printer_host or "").strip():
            dup = db.scalars(
                select(MealPrinterTerminal).where(MealPrinterTerminal.qr_auth_id == t.qr_auth_id)
            ).first()
            if not dup:
                db.add(
                    MealPrinterTerminal(
                        name=(t.name or "").strip(),
                        qr_auth_id=int(t.qr_auth_id),
                        printer_host=(t.printer_host or "").strip(),
                        printer_port=int(t.printer_port or 9100),
                        printer_stored_image_number=int(t.printer_stored_image_number or 1),
                        is_active=bool(t.is_active),
                        sort_order=int(t.sort_order or 0),
                    )
                )
        if t.qlight_enabled or (t.qlight_host or "").strip():
            dupq = db.scalars(
                select(MealQlightTerminal).where(MealQlightTerminal.qr_auth_id == t.qr_auth_id)
            ).first()
            if not dupq:
                db.add(
                    MealQlightTerminal(
                        name=(t.name or "").strip(),
                        qr_auth_id=int(t.qr_auth_id),
                        qlight_host=(t.qlight_host or "").strip(),
                        qlight_port=int(t.qlight_port or 20000),
                        is_active=bool(t.is_active),
                        sort_order=int(t.sort_order or 0),
                    )
                )

    db.execute(delete(MealQrTerminal))
    db.commit()
    logger.info("split_legacy_terminals: done (old table cleared)")
