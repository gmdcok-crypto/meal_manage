"""QR 터미널(구역별 프린터·경광등) CRUD. PC 앱 설정에서 관리."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import MealQrTerminal
from app.schemas.schemas import (
    MealQrTerminalCreate,
    MealQrTerminalUpdate,
    MealQrTerminalResponse,
)

router = APIRouter()


def legacy_device_payload_from_settings(device: dict, qr_code: str = "") -> dict:
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
        "qr_code": (qr_code or "").strip(),
    }


def terminal_to_device_payload(t: MealQrTerminal) -> dict:
    """PC 앱·WebSocket용 장치 dict (기존 device_settings 키와 동일)."""
    return {
        "printer_enabled": bool(t.printer_enabled),
        "printer_host": (t.printer_host or "").strip(),
        "printer_port": int(t.printer_port or 9100),
        "printer_stored_image_number": int(t.printer_stored_image_number or 1),
        "qlight_enabled": bool(t.qlight_enabled),
        "qlight_host": (t.qlight_host or "").strip(),
        "qlight_port": int(t.qlight_port or 20000),
        "terminal_id": t.id,
        "terminal_name": (t.name or "").strip(),
        "qr_code": (t.qr_code or "").strip(),
    }


@router.get("", response_model=List[MealQrTerminalResponse])
def list_terminals(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(
        select(MealQrTerminal).order_by(MealQrTerminal.sort_order, MealQrTerminal.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=MealQrTerminalResponse)
def create_terminal(
    body: MealQrTerminalCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    qr = (body.qr_code or "").strip()
    if not qr:
        raise HTTPException(status_code=400, detail="QR 코드(스캔 문자열)는 필수입니다.")
    dup = db.execute(select(MealQrTerminal).where(MealQrTerminal.qr_code == qr))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 등록된 QR 코드입니다.")
    row = MealQrTerminal(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{terminal_id}", response_model=MealQrTerminalResponse)
def get_terminal(
    terminal_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealQrTerminal).where(MealQrTerminal.id == terminal_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="터미널을 찾을 수 없습니다.")
    return row


@router.put("/{terminal_id}", response_model=MealQrTerminalResponse)
def update_terminal(
    terminal_id: int,
    body: MealQrTerminalUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealQrTerminal).where(MealQrTerminal.id == terminal_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="터미널을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if "qr_code" in data and data["qr_code"] is not None:
        data["qr_code"] = (data["qr_code"] or "").strip()
        if not data["qr_code"]:
            raise HTTPException(status_code=400, detail="QR 코드는 비울 수 없습니다.")
        dup = db.execute(
            select(MealQrTerminal).where(
                MealQrTerminal.qr_code == data["qr_code"],
                MealQrTerminal.id != terminal_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="이미 등록된 QR 코드입니다.")
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{terminal_id}")
def delete_terminal(
    terminal_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealQrTerminal).where(MealQrTerminal.id == terminal_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="터미널을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"ok": True}


def count_terminals(db: Session) -> int:
    r = db.execute(select(func.count()).select_from(MealQrTerminal))
    return int(r.scalar() or 0)


def find_terminal_by_qr(db: Session, qr_norm: str):
    if not qr_norm:
        return None
    result = db.execute(
        select(MealQrTerminal).where(
            MealQrTerminal.is_active.is_(True),
            MealQrTerminal.qr_code == qr_norm,
        )
    )
    return result.scalar_one_or_none()
