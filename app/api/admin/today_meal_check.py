"""당일(한국시간) 식사인증 조회 API. 관리자 폰 PWA용. 식당관리자 로그인 필수."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload
from datetime import date, datetime
from app.core.database import get_db
from app.models.models import MealLog, User, MealPolicy, CafeteriaAdmin
from app.core.time_utils import kst_today, kst_date_range_to_naive
from app.api.auth import get_current_admin
from typing import List, Optional

router = APIRouter()


@router.get("/today-meal-check")
async def today_meal_check(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: CafeteriaAdmin = Depends(get_current_admin)
):
    """한국시간 오늘 기준, 사원이름 또는 사번으로 식사인증 조회. 시간·식사종류 반환."""
    start_naive, end_naive = kst_date_range_to_naive(kst_today(), kst_today())

    query = (
        select(MealLog)
        .join(User, MealLog.user_id == User.id)
        .outerjoin(MealPolicy, MealLog.policy_id == MealPolicy.id)
        .where(
            and_(
                MealLog.created_at >= start_naive,
                MealLog.created_at < end_naive,
                MealLog.is_void == False,
            )
        )
    )
    if q and q.strip():
        query = query.where(
            or_(
                User.name.icontains(q.strip()),
                User.emp_no.icontains(q.strip())
            )
        )
    query = query.options(
        joinedload(MealLog.user),
        joinedload(MealLog.policy)
    ).order_by(MealLog.created_at.desc())
    result = await db.execute(query)
    logs = result.scalars().all()
    out = []
    for log in logs:
        time_str = log.created_at.strftime("%H:%M") if log.created_at else ""
        meal_type = (log.policy.meal_type if log.policy else "번외") or "번외"
        out.append({
            "time": time_str,
            "meal_type": meal_type,
            "name": log.user.name if log.user else "",
            "emp_no": log.user.emp_no if log.user else "",
        })
    return {"date": kst_today().isoformat(), "items": out}
