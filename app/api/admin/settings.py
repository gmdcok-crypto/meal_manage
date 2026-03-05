"""장치 설정(프린터·경광등) API. PC 앱 설정 메뉴에서 사용."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import SystemSetting
from app.schemas.schemas import DeviceSettingsResponse, DeviceSettingsUpdate
from app.core.config import settings

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
    }


async def get_device_settings_from_db(db: AsyncSession) -> dict:
    """DB에서 장치 설정 조회. 없으면 기본값 반환."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == DEVICE_KEY)
    )
    row = result.scalar_one_or_none()
    if not row or not isinstance(row.value, dict):
        return _default_device_settings()
    defaults = _default_device_settings()
    defaults.update({k: v for k, v in row.value.items() if k in defaults})
    return defaults


@router.get("/device", response_model=DeviceSettingsResponse)
async def get_device_settings(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """장치 설정 조회 (프린터·경광등 사용 여부 및 IP/포트)."""
    data = await get_device_settings_from_db(db)
    return DeviceSettingsResponse(**data)


@router.put("/device", response_model=DeviceSettingsResponse)
async def put_device_settings(
    body: DeviceSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """장치 설정 저장."""
    current = await get_device_settings_from_db(db)
    update = body.dict(exclude_unset=True)
    current.update(update)
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == DEVICE_KEY)
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = current
    else:
        db.add(SystemSetting(key=DEVICE_KEY, value=current))
    await db.commit()
    return DeviceSettingsResponse(**current)
