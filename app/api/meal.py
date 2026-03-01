from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from jose import jwt, JWTError
from app.core.database import get_db
from app.core.config import settings
from app.models.models import MealPolicy, User, MealLog
from app.schemas.schemas import MealPolicyResponse
from app.core.time_utils import kst_now, utc_now, utc_to_kst_str

router = APIRouter(prefix="/meal", tags=["meal"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/verify_device")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
    
    result = await db.execute(
        select(User).options(joinedload(User.department_ref)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="기기가 초기화되었거나 인증되지 않았습니다. 다시 로그인해 주세요."
        )
    return user

@router.get("/today", response_model=list[MealPolicyResponse])
async def get_today_policies(db: AsyncSession = Depends(get_db)):
    # 금일 활성화된 식사 정책 조회
    result = await db.execute(select(MealPolicy).where(MealPolicy.is_active == True))
    return result.scalars().all()

@router.post("/qr-scan")
async def process_qr_scan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 식사 정책 시간은 한국 시간(KST, UTC+9) 기준으로 비교 (Railway 등 서버가 UTC여도 동일 동작)
    now_time = kst_now().time()

    # 식사 시간 범위 내에 있는 정책 검색
    result = await db.execute(
        select(MealPolicy).where(
            and_(
                MealPolicy.is_active == True,
                MealPolicy.start_time <= now_time,
                MealPolicy.end_time >= now_time
            )
        )
    )
    rows = result.scalars().all()
    policy = rows[0] if rows else None

    if not policy:
        raise HTTPException(
            status_code=400,
            detail="식사 시간이 아닙니다. 식사 정책에 안내된 식사 시간에 이용해 주세요."
        )

    new_log = MealLog(
        user_id=current_user.id,
        policy_id=policy.id,
        guest_count=0,
        status="ARRIVED",
        path="QR",
        final_price=policy.base_price,
        created_at=utc_now()
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    # WebSocket Broadcast (실시간 갱신용)
    from app.api.websocket import manager
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "MEAL_LOG_CREATED",
        "data": {
            "log_id": new_log.id,
            "emp_no": current_user.emp_no,
            "name": current_user.name
        }
    }))
    
    return {
        "status": "success",
        "message": "식수 인증이 완료되었습니다.",
        "log_id": new_log.id,
        "auth_time": (utc_to_kst_str(new_log.created_at) or "").split("T")[-1][:8] if new_log.created_at else "00:00:00",
        "user": {
            "name": current_user.name,
            "emp_no": current_user.emp_no,
            "dept_name": current_user.department_name
        }
    }

@router.post("/pre-check")
async def pre_check_meal(policy_id: int, guest_count: int = 0):
    # 식사 전 사전 인증 처리
    return {"status": "ARRIVED_PRE_CHECKED", "message": "Pre-check completed"}
