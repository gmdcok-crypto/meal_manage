"""QR 터미널(구역별 프린터·경광등) CRUD. PC 앱 설정에서 관리."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.admin.settings import auth_id_to_code_map, get_device_settings_from_db
from app.api.auth import get_current_admin
from app.core.database import get_db
from app.models.models import MealQrTerminal
from app.schemas.schemas import (
    MealQrTerminalCreate,
    MealQrTerminalResponse,
    MealQrTerminalUpdate,
)

router = APIRouter()


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


def terminal_to_device_payload(t: MealQrTerminal, matched_scan: str = "") -> dict:
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
        "qr_auth_id": int(t.qr_auth_id),
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
    qid = int(body.qr_auth_id)
    if qid <= 0:
        raise HTTPException(status_code=400, detail="QR ID는 1 이상이어야 합니다.")
    _validate_qr_auth_id(db, qid)
    dup = db.execute(select(MealQrTerminal).where(MealQrTerminal.qr_auth_id == qid))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이 QR ID는 이미 다른 터미널에 연결되어 있습니다.")
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
    if "qr_auth_id" in data and data["qr_auth_id"] is not None:
        qid = int(data["qr_auth_id"])
        if qid <= 0:
            raise HTTPException(status_code=400, detail="QR ID는 1 이상이어야 합니다.")
        _validate_qr_auth_id(db, qid)
        dup = db.execute(
            select(MealQrTerminal).where(
                MealQrTerminal.qr_auth_id == qid,
                MealQrTerminal.id != terminal_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="이 QR ID는 이미 다른 터미널에 연결되어 있습니다.")
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


def find_terminal_by_scan(db: Session, qr_norm: str) -> Optional[MealQrTerminal]:
    """PWA 스캔 문자열이 허용 목록의 code 와 일치하고, 해당 id 를 쓰는 활성 터미널 반환."""
    if not qr_norm:
        return None
    device = get_device_settings_from_db(db)
    id_for_scan: Optional[int] = None
    for eid, code in auth_id_to_code_map(device).items():
        if code == qr_norm:
            id_for_scan = eid
            break
    if id_for_scan is None:
        return None
    result = db.execute(
        select(MealQrTerminal).where(
            MealQrTerminal.is_active.is_(True),
            MealQrTerminal.qr_auth_id == id_for_scan,
        )
    )
    return result.scalar_one_or_none()


# 하위 호환: 이전 import 경로
find_terminal_by_qr = find_terminal_by_scan
