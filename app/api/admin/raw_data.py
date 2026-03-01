from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.models.models import MealLog, User, MealPolicy
from app.schemas.schemas import MealLogAdminDetail, MealLogResponse, MealLogCreate, MealLogUpdate
from .utils import record_audit_log
from typing import List, Optional
from datetime import datetime, date

from app.core.time_utils import utc_now, parse_created_at_kst_to_utc, kst_date_range_to_utc_naive, kst_today

router = APIRouter(tags=["raw-data"])

@router.get("", response_model=List[MealLogAdminDetail])
async def list_raw_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    path: Optional[str] = None,
    is_void: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(MealLog)
        .outerjoin(User, MealLog.user_id == User.id)
        .outerjoin(MealPolicy, MealLog.policy_id == MealPolicy.id)
        .options(
            joinedload(MealLog.user).joinedload(User.department_ref),
            joinedload(MealLog.policy),
            joinedload(MealLog.void_operator)
        )
    )

    
    filters = []
    if start_date and end_date:
        # 사용자 선택 날짜는 KST 기준 → UTC 구간으로 변환 후 created_at(UTC) 필터
        start_utc, end_utc = kst_date_range_to_utc_naive(start_date, end_date)
        filters.append(MealLog.created_at >= start_utc)
        filters.append(MealLog.created_at < end_utc)
    elif start_date:
        # start_date만 있으면 start_date 00:00 KST ~ 오늘 끝까지
        start_utc, end_utc = kst_date_range_to_utc_naive(start_date, kst_today())
        filters.append(MealLog.created_at >= start_utc)
        filters.append(MealLog.created_at < end_utc)
    elif end_date:
        start_utc, end_utc = kst_date_range_to_utc_naive(end_date, end_date)
        filters.append(MealLog.created_at >= start_utc)
        filters.append(MealLog.created_at < end_utc)
    if search:
        filters.append(or_(
            User.name.icontains(search),
            User.emp_no.icontains(search)
        ))
    if path:
        filters.append(MealLog.path == path)
    if is_void is not None:
        filters.append(MealLog.is_void == is_void)
        
    if filters:
        query = query.where(and_(*filters))
        
    result = await db.execute(query.order_by(MealLog.created_at.desc()))
    return result.scalars().all()

@router.post("/manual", response_model=MealLogResponse)
async def create_manual_meal(
    user_id: int,
    policy_id: int,
    created_at: Optional[datetime] = None,
    guest_count: int = 0,
    reason: str = "Manual Entry",
    operator_id: int = 1, # Placeholder
    db: AsyncSession = Depends(get_db)
):
    # Fetch policy to get price snapshot
    policy_result = await db.execute(select(MealPolicy).where(MealPolicy.id == policy_id))
    policy = policy_result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Meal Policy not found")
        
    created_at_utc = parse_created_at_kst_to_utc(created_at) if created_at is not None else utc_now()
    new_log = MealLog(
        user_id=user_id,
        policy_id=policy_id,
        guest_count=guest_count,
        status="SERVED",
        path="MANUAL",
        final_price=policy.base_price,
        created_at=created_at_utc
    )
    db.add(new_log)
    await db.flush()
    
    await record_audit_log(
        db, operator_id, "CREATE", "meal_logs", new_log.id,
        after_value={
            "user_id": user_id,
            "policy_id": policy_id,
            "guest_count": guest_count,
            "path": "MANUAL"
        },
        reason=reason
    )
    
    await db.commit()
    await db.refresh(new_log)
    
    # WebSocket Broadcast (실시간 갱신용)
    from app.api.websocket import manager
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "MEAL_LOG_CREATED",
        "data": {
            "log_id": new_log.id,
            "path": "MANUAL",
            "user_id": user_id
        }
    }))
    
    return new_log

@router.patch("/{log_id}/void", response_model=MealLogResponse)
async def void_meal_log(
    log_id: int,
    reason: str,
    operator_id: int = 1, # Placeholder
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MealLog).where(MealLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Meal log not found")
    
    if log.is_void:
        raise HTTPException(status_code=400, detail="Log is already voided")
        
    log.is_void = True
    log.void_reason = reason
    log.void_operator_id = operator_id
    log.voided_at = utc_now()
    
    await record_audit_log(
        db, operator_id, "VOID", "meal_logs", log.id,
        before_value={"is_void": False},
        after_value={"is_void": True, "void_reason": reason},
        reason="Admin voiding"
    )
    
    await db.commit()
    await db.refresh(log)
    
    # WebSocket Broadcast (실시간 갱신용)
    from app.api.websocket import manager
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "MEAL_LOG_VOIDED",
        "data": {
            "log_id": log.id
        }
    }))
    
    return log

@router.put("/{log_id}", response_model=MealLogResponse)
async def update_raw_data(
    log_id: int,
    update_data: MealLogUpdate,
    operator_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MealLog).where(MealLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Meal log not found")
        
    before_value = {
        "user_id": log.user_id,
        "policy_id": log.policy_id,
        "created_at": str(log.created_at),
        "guest_count": log.guest_count
    }
    
    if update_data.user_id is not None: log.user_id = update_data.user_id
    if update_data.policy_id is not None:
        policy_result = await db.execute(select(MealPolicy).where(MealPolicy.id == update_data.policy_id))
        policy = policy_result.scalar_one_or_none()
        if policy:
            log.policy_id = update_data.policy_id
            log.final_price = policy.base_price
    if update_data.created_at is not None:
        log.created_at = parse_created_at_kst_to_utc(update_data.created_at) or update_data.created_at
    if update_data.guest_count is not None: log.guest_count = update_data.guest_count
    
    await record_audit_log(
        db, operator_id, "UPDATE", "meal_logs", log.id,
        before_value=before_value,
        after_value={
            "user_id": log.user_id,
            "policy_id": log.policy_id,
            "created_at": str(log.created_at),
            "guest_count": log.guest_count
        },
        reason=update_data.reason or "Admin update"
    )
    
    await db.commit()
    await db.refresh(log)
    return log

@router.delete("/{log_id}")
async def delete_raw_data(
    log_id: int,
    operator_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MealLog).where(MealLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Meal log not found")
        
    await record_audit_log(
        db, operator_id, "DELETE", "meal_logs", log.id,
        before_value={"id": log.id, "user_id": log.user_id},
        reason="Admin physical delete"
    )
    
    await db.delete(log)
    await db.commit()
    return {"message": "Deleted successfully"}
