"""식당관리(위탁사 운영자) CRUD 및 기기 초기화. PC 앱 관리자 메뉴용. cafeteria_admins 테이블 사용."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import CafeteriaAdmin
from app.schemas.schemas import CafeteriaAdminResponse, AdminCreate, AdminUpdate
from typing import List

router = APIRouter()


@router.get("", response_model=List[CafeteriaAdminResponse])
async def list_admins(db: AsyncSession = Depends(get_db)):
    """식당관리 목록 (사번, 이름, 인증 상태)."""
    result = await db.execute(
        select(CafeteriaAdmin).order_by(CafeteriaAdmin.emp_no)
    )
    return result.scalars().all()


@router.post("", response_model=CafeteriaAdminResponse)
async def create_admin(
    body: AdminCreate,
    db: AsyncSession = Depends(get_db)
):
    """식당관리 등록. 최초 로그인 시 비밀번호 설정·기기 인증."""
    existing = await db.execute(select(CafeteriaAdmin).where(CafeteriaAdmin.emp_no == body.emp_no))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 존재하는 사번입니다.")
    admin = CafeteriaAdmin(
        emp_no=body.emp_no.strip(),
        name=body.name.strip(),
        is_verified=False,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


@router.put("/{admin_id}", response_model=CafeteriaAdminResponse)
async def update_admin(
    admin_id: int,
    body: AdminUpdate,
    db: AsyncSession = Depends(get_db)
):
    """식당관리 수정 (이름 등)."""
    result = await db.execute(select(CafeteriaAdmin).where(CafeteriaAdmin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="관리자를 찾을 수 없습니다.")
    if body.name is not None:
        admin.name = body.name.strip()
    await db.commit()
    await db.refresh(admin)
    return admin


@router.delete("/{admin_id}")
async def delete_admin(admin_id: int, db: AsyncSession = Depends(get_db)):
    """식당관리 삭제."""
    result = await db.execute(select(CafeteriaAdmin).where(CafeteriaAdmin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="관리자를 찾을 수 없습니다.")
    await db.delete(admin)
    await db.commit()
    return {"message": "삭제되었습니다."}


@router.post("/{admin_id}/reset-device")
async def reset_admin_device(admin_id: int, db: AsyncSession = Depends(get_db)):
    """식당관리 기기 초기화. 다음 로그인 시 비밀번호 재설정."""
    result = await db.execute(select(CafeteriaAdmin).where(CafeteriaAdmin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="관리자를 찾을 수 없습니다.")
    admin.is_verified = False
    admin.password_hash = None
    await db.commit()
    return {"message": "기기 인증이 초기화되었습니다."}
