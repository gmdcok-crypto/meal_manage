"""기존 meal_qr_terminals.qr_code → qr_auth_id 및 device.allowed_qr_entries 보강 (MySQL)."""
import logging
from sqlalchemy import text, select
from sqlalchemy.orm import sessionmaker

from app.models.models import SystemSetting

logger = logging.getLogger(__name__)

DEVICE_KEY = "device"


def _schema_name(engine) -> str:
    from app.core.config import settings

    return settings.DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]


def _next_entry_id(entries: list) -> int:
    return max((e["id"] for e in entries), default=0) + 1


def ensure_meal_qr_terminals_auth_columns(engine) -> None:
    if engine.dialect.name != "mysql":
        logger.info("meal_qr_terminal_migration: skip dialect %s", engine.dialect.name)
        return
    dbn = _schema_name(engine)
    with engine.begin() as conn:
        r = conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'meal_qr_terminals'"
            ),
            {"db": dbn},
        )
        cols = {row[0] for row in r.fetchall()}
        if not cols:
            return
        if "qr_auth_id" not in cols:
            try:
                conn.execute(text("ALTER TABLE meal_qr_terminals ADD COLUMN qr_auth_id INT NULL"))
                logger.info("meal_qr_terminals: added qr_auth_id")
            except Exception as e:
                logger.warning("meal_qr_terminals add qr_auth_id: %s", e)


def run_meal_qr_terminal_migration(engine) -> None:
    if engine.dialect.name != "mysql":
        return
    ensure_meal_qr_terminals_auth_columns(engine)
    dbn = _schema_name(engine)
    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'meal_qr_terminals'"
            ),
            {"db": dbn},
        )
        cols = {row[0] for row in r.fetchall()}
    if "qr_code" not in cols:
        _finalize_constraints(engine, dbn)
        return
    if "qr_auth_id" not in cols:
        logger.warning("meal_qr migration: qr_code exists but qr_auth_id missing")
        return

    from app.api.admin.settings import _default_device_settings, coalesce_allowed_qr_entries

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        result = db.execute(select(SystemSetting).where(SystemSetting.key == DEVICE_KEY))
        row = result.scalar_one_or_none()
        device = _default_device_settings()
        if row and isinstance(row.value, dict):
            for k, v in row.value.items():
                if k in device:
                    device[k] = v
        entries = coalesce_allowed_qr_entries(device)
        if not entries:
            entries = [{"id": 1, "code": "migrated_qr"}]

        with engine.connect() as conn2:
            trows = list(
                conn2.execute(text("SELECT id, qr_code, qr_auth_id FROM meal_qr_terminals"))
            )

        def code_for_norm(norm: str) -> int:
            nonlocal entries
            for e in entries:
                if e["code"] == norm:
                    return e["id"]
            nid = _next_entry_id(entries)
            entries.append({"id": nid, "code": norm})
            return nid

        updates = []
        for tid, qr_code, existing_aid in trows:
            if existing_aid is not None:
                continue
            norm = (qr_code or "").strip().replace("\ufeff", "").replace("\r", "").replace("\n", "").strip()
            if not norm:
                logger.warning("meal_qr migration: terminal id=%s empty qr_code, skip", tid)
                continue
            eid = code_for_norm(norm)
            updates.append((tid, eid))

        device["allowed_qr_entries"] = entries
        if "allowed_qr_list" in device:
            del device["allowed_qr_list"]

        if row:
            row.value = device
        else:
            db.add(SystemSetting(key=DEVICE_KEY, value=device))
        db.commit()

        with engine.begin() as conn:
            for tid, eid in updates:
                conn.execute(
                    text("UPDATE meal_qr_terminals SET qr_auth_id = :eid WHERE id = :tid"),
                    {"eid": eid, "tid": tid},
                )

        with engine.begin() as conn:
            res = conn.execute(
                text("SHOW INDEX FROM meal_qr_terminals WHERE Column_name = 'qr_code'")
            )
            key_names = {row[2] for row in res.fetchall()}
            for kn in key_names:
                if kn and kn != "PRIMARY":
                    conn.execute(text(f"ALTER TABLE meal_qr_terminals DROP INDEX `{kn}`"))
            conn.execute(text("ALTER TABLE meal_qr_terminals DROP COLUMN qr_code"))
            conn.execute(text("ALTER TABLE meal_qr_terminals MODIFY qr_auth_id INT NOT NULL"))
            try:
                conn.execute(
                    text(
                        "ALTER TABLE meal_qr_terminals ADD UNIQUE KEY uq_meal_qr_terminals_qr_auth (qr_auth_id)"
                    )
                )
            except Exception as e:
                if "Duplicate" not in str(e) and "1061" not in str(e):
                    logger.warning("meal_qr unique qr_auth_id: %s", e)
        logger.info("meal_qr_terminals: migrated qr_code → qr_auth_id")
    except Exception as e:
        logger.exception("meal_qr_terminal_migration failed: %s", e)
        db.rollback()
    finally:
        db.close()


def _finalize_constraints(engine, dbn: str) -> None:
    """이미 qr_code 가 제거된 DB: qr_auth_id NOT NULL·유니크 보강."""
    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'meal_qr_terminals' AND COLUMN_NAME = 'qr_auth_id'"
            ),
            {"db": dbn},
        )
        row = r.fetchone()
        if not row:
            return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE meal_qr_terminals MODIFY qr_auth_id INT NOT NULL"))
    except Exception as e:
        logger.debug("meal_qr finalize NOT NULL: %s", e)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE meal_qr_terminals ADD UNIQUE KEY uq_meal_qr_terminals_qr_auth (qr_auth_id)"
                )
            )
    except Exception as e:
        if "Duplicate" not in str(e) and "1061" not in str(e):
            logger.debug("meal_qr finalize unique: %s", e)
