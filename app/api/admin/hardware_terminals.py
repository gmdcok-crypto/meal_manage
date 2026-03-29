"""구역별 프린터·경광등: 별도 테이블·CRUD. WebSocket device 페이로드는 두 행을 합쳐 생성."""
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.admin.settings import auth_id_to_code_map, get_device_settings_from_db
from app.api.auth import get_current_admin
from app.core.database import get_db
from app.models.models import MealPrinterTerminal, MealQlightTerminal
from app.schemas.schemas import (
    MealPrinterTerminalCreate,
    MealPrinterTerminalResponse,
    MealPrinterTerminalUpdate,
    MealQlightTerminalCreate,
    MealQlightTerminalResponse,
    MealQlightTerminalUpdate,
)

printer_router = APIRouter()
qlight_router = APIRouter()


def legacy_device_payload_from_settings(device: dict, matched_scan: str = "") -> dict:
    """system_settings device JSON → PC/WebSocket용 dict."""
    return {
        "printer_enabled": bool(device.get("printer_enabled")),
        "printer_host": (device.get("printer_host") or "").strip(),
        "printer_port": int(device.get("printer_port") or 9100),
        "printer_stored_image_number": int(device.get("printer_stored_image_number") or 1),
        "qlight_enabled": bool(device.get("qlight_enabled")),
        "qlight_host": (device.get("qlight_host") or "").strip(),
        "qlight_port": int(device.get("qlight_port") or 20000),
        "terminal_id": None,
        "terminal_name": "",
        "qr_auth_id": None,
        "qr_code": (matched_scan or "").strip(),
    }


def _validate_qr_auth_id(db: Session, qr_auth_id: int) -> None:
    device = get_device_settings_from_db(db)
    m = auth_id_to_code_map(device)
    if qr_auth_id not in m:
        raise HTTPException(
            status_code=400,
            detail="등록되지 않은 QR ID입니다. 먼저 「인증 QR」에서 ID·스캔 문자열을 저장하세요.",
        )


def count_printer_terminals(db: Session) -> int:
    return int(db.execute(select(func.count()).select_from(MealPrinterTerminal)).scalar_one() or 0)


def count_qlight_terminals(db: Session) -> int:
    return int(db.execute(select(func.count()).select_from(MealQlightTerminal)).scalar_one() or 0)


def total_hardware_rows(db: Session) -> int:
    return count_printer_terminals(db) + count_qlight_terminals(db)


def qr_auth_ids_in_use(db: Session) -> Set[int]:
    p = db.scalars(select(MealPrinterTerminal.qr_auth_id)).all()
    q = db.scalars(select(MealQlightTerminal.qr_auth_id)).all()
    out: Set[int] = set()
    for x in p:
        if x is not None:
            out.add(int(x))
    for x in q:
        if x is not None:
            out.add(int(x))
    return out


def auth_id_for_normalized_scan(db: Session, qr_norm: str) -> Optional[int]:
    if not qr_norm:
        return None
    device = get_device_settings_from_db(db)
    for eid, code in auth_id_to_code_map(device).items():
        if code == qr_norm:
            return int(eid)
    return None


def has_binding_for_auth_id(db: Session, auth_id: int) -> bool:
    p = db.scalars(
        select(MealPrinterTerminal).where(
            MealPrinterTerminal.qr_auth_id == auth_id,
            MealPrinterTerminal.is_active.is_(True),
        )
    ).first()
    if p:
        return True
    q = db.scalars(
        select(MealQlightTerminal).where(
            MealQlightTerminal.qr_auth_id == auth_id,
            MealQlightTerminal.is_active.is_(True),
        )
    ).first()
    return q is not None


def build_merged_device_payload(db: Session, auth_id: int, matched_scan: str = "") -> dict:
    p = db.scalars(select(MealPrinterTerminal).where(MealPrinterTerminal.qr_auth_id == auth_id)).first()
    q = db.scalars(select(MealQlightTerminal).where(MealQlightTerminal.qr_auth_id == auth_id)).first()
    p_on = p is not None and bool(p.is_active)
    q_on = q is not None and bool(q.is_active)
    return {
        "printer_enabled": p_on,
        "printer_host": (p.printer_host or "").strip() if p else "",
        "printer_port": int(p.printer_port or 9100) if p else 9100,
        "printer_stored_image_number": int(p.printer_stored_image_number or 1) if p else 1,
        "qlight_enabled": q_on,
        "qlight_host": (q.qlight_host or "").strip() if q else "",
        "qlight_port": int(q.qlight_port or 20000) if q else 20000,
        "terminal_id": (p.id if p else (q.id if q else None)),
        "terminal_name": ((p.name or "").strip() if p else ((q.name or "").strip() if q else "")),
        "qr_auth_id": int(auth_id),
        "qr_code": (matched_scan or "").strip(),
    }


# --- 프린터 CRUD
@printer_router.get("", response_model=List[MealPrinterTerminalResponse])
def list_printer_terminals(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(
        select(MealPrinterTerminal).order_by(MealPrinterTerminal.sort_order, MealPrinterTerminal.id)
    )
    return list(result.scalars().all())


@printer_router.post("", response_model=MealPrinterTerminalResponse)
def create_printer_terminal(
    body: MealPrinterTerminalCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    qid = int(body.qr_auth_id)
    if qid <= 0:
        raise HTTPException(status_code=400, detail="QR ID는 1 이상이어야 합니다.")
    _validate_qr_auth_id(db, qid)
    dup = db.scalars(select(MealPrinterTerminal).where(MealPrinterTerminal.qr_auth_id == qid)).first()
    if dup:
        raise HTTPException(status_code=400, detail="이 QR ID에는 이미 프린터가 등록되어 있습니다.")
    row = MealPrinterTerminal(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@printer_router.get("/{tid}", response_model=MealPrinterTerminalResponse)
def get_printer_terminal(
    tid: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = db.get(MealPrinterTerminal, tid)
    if not row:
        raise HTTPException(status_code=404, detail="프린터 등록을 찾을 수 없습니다.")
    return row


@printer_router.put("/{tid}", response_model=MealPrinterTerminalResponse)
def update_printer_terminal(
    tid: int,
    body: MealPrinterTerminalUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = db.get(MealPrinterTerminal, tid)
    if not row:
        raise HTTPException(status_code=404, detail="프린터 등록을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if "qr_auth_id" in data and data["qr_auth_id"] is not None:
        qid = int(data["qr_auth_id"])
        if qid <= 0:
            raise HTTPException(status_code=400, detail="QR ID는 1 이상이어야 합니다.")
        _validate_qr_auth_id(db, qid)
        dup = db.scalars(
            select(MealPrinterTerminal).where(
                MealPrinterTerminal.qr_auth_id == qid,
                MealPrinterTerminal.id != tid,
            )
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="이 QR ID에는 이미 다른 프린터가 등록되어 있습니다.")
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@printer_router.delete("/{tid}")
def delete_printer_terminal(
    tid: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = db.get(MealPrinterTerminal, tid)
    if not row:
        raise HTTPException(status_code=404, detail="프린터 등록을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- 경광등 CRUD
@qlight_router.get("", response_model=List[MealQlightTerminalResponse])
def list_qlight_terminals(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(
        select(MealQlightTerminal).order_by(MealQlightTerminal.sort_order, MealQlightTerminal.id)
    )
    return list(result.scalars().all())


@qlight_router.post("", response_model=MealQlightTerminalResponse)
def create_qlight_terminal(
    body: MealQlightTerminalCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    qid = int(body.qr_auth_id)
    if qid <= 0:
        raise HTTPException(status_code=400, detail="QR ID는 1 이상이어야 합니다.")
    _validate_qr_auth_id(db, qid)
    dup = db.scalars(select(MealQlightTerminal).where(MealQlightTerminal.qr_auth_id == qid)).first()
    if dup:
        raise HTTPException(status_code=400, detail="이 QR ID에는 이미 경광등이 등록되어 있습니다.")
    row = MealQlightTerminal(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@qlight_router.get("/{tid}", response_model=MealQlightTerminalResponse)
def get_qlight_terminal(
    tid: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = db.get(MealQlightTerminal, tid)
    if not row:
        raise HTTPException(status_code=404, detail="경광등 등록을 찾을 수 없습니다.")
    return row


@qlight_router.put("/{tid}", response_model=MealQlightTerminalResponse)
def update_qlight_terminal(
    tid: int,
    body: MealQlightTerminalUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = db.get(MealQlightTerminal, tid)
    if not row:
        raise HTTPException(status_code=404, detail="경광등 등록을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if "qr_auth_id" in data and data["qr_auth_id"] is not None:
        qid = int(data["qr_auth_id"])
        if qid <= 0:
            raise HTTPException(status_code=400, detail="QR ID는 1 이상이어야 합니다.")
        _validate_qr_auth_id(db, qid)
        dup = db.scalars(
            select(MealQlightTerminal).where(
                MealQlightTerminal.qr_auth_id == qid,
                MealQlightTerminal.id != tid,
            )
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="이 QR ID에는 이미 다른 경광등이 등록되어 있습니다.")
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@qlight_router.delete("/{tid}")
def delete_qlight_terminal(
    tid: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    row = db.get(MealQlightTerminal, tid)
    if not row:
        raise HTTPException(status_code=404, detail="경광등 등록을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"ok": True}
