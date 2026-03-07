from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import MealLog, MealPolicy, User
from app.schemas.schemas import DashboardStats
from app.core.time_utils import kst_now, kst_today, kst_date_range_naive
from datetime import date, datetime, timedelta

router = APIRouter(tags=["dashboard"])

# 식사 종류 표시 순서 (야식(심야) → 야식(새벽), 심야/새벽 분리 정책도 동일 적용)
MEAL_TYPE_DISPLAY_ORDER = ("조식", "중식", "석식", "야식(심야)", "야식(새벽)")


def _policy_display_order_key(policy):
    """meal_type 기준 고정 표시 순서. 목록에 없으면 뒤로."""
    order_map = {t: i for i, t in enumerate(MEAL_TYPE_DISPLAY_ORDER)}
    return (order_map.get(policy.meal_type, 999), policy.meal_type or "")


@router.get("/today", response_model=DashboardStats)
async def get_today_stats(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    today = kst_today()
    
    # Determined meal type (한국 시간 기준)
    hour = kst_now().hour
    if hour < 10: meal_type_key = "breakfast"
    elif hour < 16: meal_type_key = "lunch"
    else: meal_type_key = "dinner"
    
    # Get all active policies for breakdown (정렬: 일반 식사 순서, 자정 넘김은 심야→새벽)
    policy_query = select(MealPolicy).where(MealPolicy.is_active == True).order_by(MealPolicy.start_time)
    policy_result = await db.execute(policy_query)
    policies = sorted(policy_result.scalars().all(), key=_policy_display_order_key)
    
    # Get all logs for today (created_at은 KST naive로 저장됨)
    start_naive, end_naive = kst_date_range_naive()
    log_query = select(MealLog).outerjoin(MealPolicy, MealLog.policy_id == MealPolicy.id).where(
        and_(
            MealLog.is_void == False,
            MealLog.created_at >= start_naive,
            MealLog.created_at < end_naive,
        )
    )
    log_result = await db.execute(log_query)
    logs = log_result.scalars().all()
    
    # Exception criteria: 
    # 1. is_void == True (Cancelled)
    # 2. policy_id is None (Extra/No categorization)
    exception_logs = [log for log in logs if log.is_void or log.policy_id is None]
    
    # Active/Valid logs for policy breakdown (Not voided AND has policy_id)
    valid_logs = [log for log in logs if not log.is_void and log.policy_id is not None]
    
    # Total count = sum of (1 + guest_count) for all NON-VOID logs
    # Note: Even if it's "Extra", it counts as a meal if not voided.
    non_void_logs = [log for log in logs if not log.is_void]
    total_count = sum(1 + log.guest_count for log in non_void_logs)
    
    # Policy summary breakdown
    meal_summaries = []
    for policy in policies:
        policy_logs = [log for log in valid_logs if log.policy_id == policy.id]
        count = sum(1 + log.guest_count for log in policy_logs)
        meal_summaries.append({
            "meal_type": policy.meal_type,
            "count": count,
            "price": policy.base_price
        })
    
    return DashboardStats(
        date=today,
        meal_type=meal_type_key,
        total_count=total_count,
        employee_count=len([l for l in non_void_logs if l.policy_id is not None]), # Real employees with policy
        guest_count=sum(log.guest_count for log in non_void_logs),
        exception_count=len(exception_logs),
        meal_summaries=meal_summaries
    )
