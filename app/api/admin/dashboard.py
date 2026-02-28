from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.models.models import MealLog, MealPolicy, User
from app.schemas.schemas import DashboardStats
from datetime import date, datetime
from typing import List

router = APIRouter(tags=["dashboard"])

@router.get("/today", response_model=DashboardStats)
async def get_today_stats(db: AsyncSession = Depends(get_db)):
    today = date.today()
    
    # Determined meal type (Simplified for now: based on current hour)
    hour = datetime.now().hour
    if hour < 10: meal_type_key = "breakfast"
    elif hour < 16: meal_type_key = "lunch"
    else: meal_type_key = "dinner"
    
    # Get all active policies for breakdown
    policy_query = select(MealPolicy).where(MealPolicy.is_active == True).order_by(MealPolicy.start_time)
    policy_result = await db.execute(policy_query)
    policies = policy_result.scalars().all()
    
    # Get all logs for today
    log_query = select(MealLog).where(func.date(MealLog.created_at) == today)
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
        # Sum logs for this specific policy
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
