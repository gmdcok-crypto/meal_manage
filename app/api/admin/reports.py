from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.models.models import MealLog, User, MealPolicy, Department
from app.core.time_utils import kst_date_range_to_utc_naive, utc_to_kst_str
from datetime import date, datetime, timedelta
from typing import List, Optional

router = APIRouter(tags=["reports"])

@router.get("/daily")
async def get_daily_report(
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    start_utc, end_utc = kst_date_range_to_utc_naive(target_date, target_date)
    query = select(
        MealPolicy.meal_type,
        func.count(MealLog.id).label("employee_count"),
        func.sum(MealLog.guest_count).label("guest_count")
    ).join(MealLog, MealPolicy.id == MealLog.policy_id)\
     .where(and_(
        MealLog.created_at >= start_utc,
        MealLog.created_at < end_utc,
        MealLog.is_void == False
    ))\
     .group_by(MealPolicy.meal_type)
    
    result = await db.execute(query)
    return [dict(row._asdict()) for row in result.all()]

@router.get("/monthly")
async def get_monthly_report(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db)
):
    start_date = date(year, month, 1)
    end_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    end_date_last = end_date - timedelta(days=1)  # 해당 월 마지막 날
    start_utc, end_utc = kst_date_range_to_utc_naive(start_date, end_date_last)

    # created_at은 UTC → 일자별 집계는 KST 날짜 기준으로 (Python에서 그룹핑)
    query = select(MealLog).where(and_(
        MealLog.created_at >= start_utc,
        MealLog.created_at < end_utc,
        MealLog.is_void == False
    ))
    result = await db.execute(query)
    logs = result.scalars().all()

    from collections import defaultdict
    by_date = defaultdict(lambda: {"employee_count": 0, "guest_count": 0, "total_amount": 0})
    for log in logs:
        kst_date_str = (utc_to_kst_str(log.created_at) or "")[:10]
        if not kst_date_str:
            continue
        by_date[kst_date_str]["employee_count"] += 1
        by_date[kst_date_str]["guest_count"] += (log.guest_count or 0)
        by_date[kst_date_str]["total_amount"] += (log.final_price or 0) * (1 + (log.guest_count or 0))

    return [
        {"date": d, "employee_count": v["employee_count"], "guest_count": v["guest_count"], "total_amount": v["total_amount"]}
        for d in sorted(by_date.keys())
        for v in [by_date[d]]
    ]

@router.get("/department")
async def get_department_report(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
):
    start_utc, end_utc = kst_date_range_to_utc_naive(start_date, end_date)
    query = select(
        Department.name.label("department_name"),
        func.count(MealLog.id).label("count"),
        func.sum(MealLog.guest_count).label("guest_count")
    ).join(MealLog, User.id == MealLog.user_id)\
     .join(Department, User.department_id == Department.id)\
     .where(and_(
        MealLog.created_at >= start_utc,
        MealLog.created_at < end_utc,
        MealLog.is_void == False
     )).group_by(Department.name)
     
    result = await db.execute(query)
    return [dict(row._asdict()) for row in result.all()]

@router.get("/excel")
async def get_excel_report(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db)
):
    import pandas as pd
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from sqlalchemy.orm import joinedload
    
    start_date = date(year, month, 1)
    end_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    end_date_last = end_date - timedelta(days=1)
    start_utc, end_utc = kst_date_range_to_utc_naive(start_date, end_date_last)
    
    query = select(MealLog).options(
        joinedload(MealLog.user).joinedload(User.department_ref),
        joinedload(MealLog.policy)
    ).where(and_(
        MealLog.created_at >= start_utc,
        MealLog.created_at < end_utc,
        MealLog.is_void == False
    ))
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        # Return empty excel or handle as needed
        pass

    # Prepare data for DataFrames (날짜는 KST 기준 표시)
    data = []
    for log in logs:
        kst_date_str = (utc_to_kst_str(log.created_at) or "")[:10]
        data.append({
            "날짜": kst_date_str or (log.created_at.date() if log.created_at else ""),
            "사번": log.user.emp_no if log.user else "N/A",
            "이름": log.user.name if log.user else "N/A",
            "부서": log.user.department_name if log.user else "N/A",
            "식사종류": log.policy.meal_type if log.policy else "번외",
            "인원": 1 + log.guest_count,
            "단가": log.final_price,
            "금액": log.final_price * (1 + log.guest_count)
        })
    
    df_raw = pd.DataFrame(data)
    
    # Sheet 1: 부서별 합계
    df_dept = df_raw.groupby("부서").agg({
        "인원": "sum",
        "금액": "sum"
    }).reset_index()
    df_dept.columns = ["부서명", "총 식수", "총 금액"]
    
    # Sheet 2: 개인별 합계
    df_user = df_raw.groupby(["사번", "이름", "부서"]).agg({
        "인원": "sum",
        "금액": "sum"
    }).reset_index()
    df_user.columns = ["사번", "이름", "부서", "총 식수", "총 금액"]
    
    # Sheet 3: 일자별 합계
    df_daily = df_raw.groupby("날짜").agg({
        "인원": "sum",
        "금액": "sum"
    }).reset_index()
    
    # Create Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_dept.to_sheet = "부서별합계"
        df_dept.to_excel(writer, sheet_name="부서별합계", index=False)
        df_user.to_excel(writer, sheet_name="개인별합계", index=False)
        df_daily.to_excel(writer, sheet_name="일자별합계", index=False)
    
    output.seek(0)
    filename = f"MealReport_{year}{month:02d}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
