"""장치 설정(프린터·경광등) API. PC 앱 설정 메뉴에서 사용."""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import SystemSetting
from app.schemas.schemas import AuthQrEntry, DeviceSettingsResponse, DeviceSettingsUpdate

router = APIRouter()
DEVICE_KEY = "device"


def _default_device_settings() -> dict:
    """DB에 없을 때 환경변수(config) fallback."""
    return {
        "printer_enabled": bool(settings.PRINTER_HOST and str(settings.PRINTER_HOST).strip()),
        "printer_host": (settings.PRINTER_HOST or "").strip(),
        "printer_port": getattr(settings, "PRINTER_PORT", 9100),
        "printer_stored_image_number": getattr(settings, "PRINTER_STORED_IMAGE_NUMBER", 1),
        "qlight_enabled": False,
        "qlight_host": (getattr(settings, "QLIGHT_HOST", None) or "").strip(),
        "qlight_port": getattr(settings, "QLIGHT_PORT", 20000),
        "allowed_qr_entries": [
            {"id": 1, "code": "bluecom_meal_management"},
        ],
    }


def coalesce_allowed_qr_entries(device: dict) -> List[Dict[str, Any]]:
    """allowed_qr_entries 우선, 없으면 레거시 allowed_qr_list 를 id 부여하여 변환."""
    ent = device.get("allowed_qr_entries")
    if isinstance(ent, list) and ent:
        out = []
        for x in ent:
            if isinstance(x, dict) and x.get("id") is not None:
                c = str(x.get("code") or "").strip()
                if c:
                    out.append({"id": int(x["id"]), "code": c})
        if out:
            return out
    old = device.get("allowed_qr_list") or []
    if isinstance(old, list):
        return [
            {"id": i + 1, "code": str(s).strip()}
            for i, s in enumerate(old)
            if str(s).strip()
        ]
    return []


def normalize_allowed_qr_entries(entries: List[AuthQrEntry]) -> List[Dict[str, Any]]:
    """저장용: id·code 정리, id 없으면 자동 부여, code 중복 제거."""
    seen_code: set = set()
    seen_id: set = set()
    out: List[Dict[str, Any]] = []
    next_id = 1
    for e in entries:
        code = str(e.code or "").strip()
        if not code or code in seen_code:
            continue
        eid = int(e.id) if e.id and e.id > 0 else 0
        if eid in seen_id:
            eid = 0
        if eid <= 0:
            eid = next_id
            while eid in seen_id:
                eid += 1
        seen_id.add(eid)
        seen_code.add(code)
        out.append({"id": eid, "code": code})
        next_id = max(next_id, eid + 1)
    out.sort(key=lambda x: x["id"])
    return out


def get_device_settings_from_db(db: Session) -> dict:
    """DB에서 장치 설정 조회. 없으면 기본값 반환."""
    result = db.execute(select(SystemSetting).where(SystemSetting.key == DEVICE_KEY))
    row = result.scalar_one_or_none()
    defaults = _default_device_settings()
    combined = dict(defaults)
    if row is not None and isinstance(row.value, dict):
        combined.update(row.value)
    entries = coalesce_allowed_qr_entries(combined)
    out = {k: combined.get(k, defaults[k]) for k in defaults}
    out["allowed_qr_entries"] = entries
    return out


def auth_id_to_code_map(device: dict) -> Dict[int, str]:
    m: Dict[int, str] = {}
    for e in coalesce_allowed_qr_entries(device):
        m[int(e["id"])] = e["code"]
    return m


@router.get("/device", response_model=DeviceSettingsResponse)
def get_device_settings(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """장치 설정 조회 (프린터·경광등 사용 여부 및 IP/포트)."""
    data = get_device_settings_from_db(db)
    return DeviceSettingsResponse(**data)


@router.put("/device", response_model=DeviceSettingsResponse)
def put_device_settings(
    body: DeviceSettingsUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """장치 설정 저장."""
    current = get_device_settings_from_db(db)
    update = body.model_dump(exclude_unset=True)
    if "allowed_qr_entries" in update and update["allowed_qr_entries"] is not None:
        from app.api.admin.hardware_terminals import qr_auth_ids_in_use

        raw_list = [
            AuthQrEntry.model_validate(x) if isinstance(x, dict) else x
            for x in update["allowed_qr_entries"]
        ]
        normalized = normalize_allowed_qr_entries(raw_list)
        new_ids = {e["id"] for e in normalized}
        t_rows = qr_auth_ids_in_use(db)
        for aid in t_rows:
            if aid is not None and aid not in new_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"QR ID {aid} 는 터미널에서 사용 중이라 목록에서 삭제할 수 없습니다.",
                )
        update["allowed_qr_entries"] = normalized
        update.pop("allowed_qr_list", None)
    current.update(update)
    if "allowed_qr_list" in current:
        del current["allowed_qr_list"]
    current["allowed_qr_entries"] = coalesce_allowed_qr_entries(current)

    result = db.execute(select(SystemSetting).where(SystemSetting.key == DEVICE_KEY))
    row = result.scalar_one_or_none()
    if row:
        row.value = current
    else:
        db.add(SystemSetting(key=DEVICE_KEY, value=current))
    db.commit()
    return DeviceSettingsResponse(**current)
