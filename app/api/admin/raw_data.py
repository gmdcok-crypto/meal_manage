from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import MealLog, User, MealPolicy
from app.schemas.schemas import MealLogAdminDetail, MealLogResponse, MealLogCreate, MealLogUpdate
from .utils import record_audit_log
from typing import List, Optional
from datetime import datetime, date
from pydantic import ValidationError

from app.core.time_utils import utc_now, parse_created_at_kst_to_utc, kst_date_range_to_naive, kst_today, KST

router = APIRouter(tags=["raw-data"])

@router.get("", response_model=List[MealLogAdminDetail])
def list_raw_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    path: Optional[str] = None,
    is_void: Optional[bool] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    # selectinload: 비동기 세션에서 joinedload+수동 outerjoin 조합은 관계 미로딩 → lazy 접근 시 MissingGreenlet(500) 유발 가능
    query = select(MealLog).options(
        selectinload(MealLog.user).selectinload(User.department_ref),
        selectinload(MealLog.policy),
        # void_operator도 User → department_name 프로퍼티가 department_ref 접근 → 미로딩 시 MissingGreenlet(500)
        selectinload(MealLog.void_operator).selectinload(User.department_ref),
    )

    filters = []
    if search:
        query = query.join(User, MealLog.user_id == User.id)
        filters.append(
            or_(
                User.name.icontains(search),
                User.emp_no.icontains(search),
            )
        )
    if start_date and end_date:
        # 사용자 선택 날짜는 KST 기준, created_at(KST naive) 필터
        start_naive, end_naive = kst_date_range_to_naive(start_date, end_date)
        filters.append(MealLog.created_at >= start_naive)
        filters.append(MealLog.created_at < end_naive)
    elif start_date:
        # start_date만 있으면 start_date 00:00 KST ~ 오늘 끝까지
        start_naive, end_naive = kst_date_range_to_naive(start_date, kst_today())
        filters.append(MealLog.created_at >= start_naive)
        filters.append(MealLog.created_at < end_naive)
    elif end_date:
        start_naive, end_naive = kst_date_range_to_naive(end_date, end_date)
        filters.append(MealLog.created_at >= start_naive)
        filters.append(MealLog.created_at < end_naive)
    if path:
        filters.append(MealLog.path == path)
    if is_void is not None:
        filters.append(MealLog.is_void == is_void)
        
    if filters:
        query = query.where(and_(*filters))
        
    result = db.execute(query.order_by(MealLog.created_at.desc()))
    logs = result.scalars().all()

    # 직렬화 실패 시 해당 로그만 제외하고 응답 (보고서 등에서 500 방지)
    out: List[MealLogAdminDetail] = []
    for log in logs:
        try:
            out.append(MealLogAdminDetail.model_validate(log))
        except (ValidationError, TypeError, ValueError) as e:
            import logging
            logging.getLogger(__name__).warning("raw_data skip log id=%s: %s", getattr(log, "id", None), e)
            continue
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "raw_data skip log id=%s (unexpected): %s",
                getattr(log, "id", None),
                e,
                exc_info=True,
            )
            continue
    return out

@router.post("/manual", response_model=MealLogResponse)
def create_manual_meal(
    user_id: int,
    policy_id: int,
    background_tasks: BackgroundTasks,
    created_at: Optional[datetime] = None,
    guest_count: int = 0,
    reason: str = "Manual Entry",
    operator_id: int = 1, # Placeholder
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    # Fetch policy to get price snapshot
    policy_result = db.execute(select(MealPolicy).where(MealPolicy.id == policy_id))
    policy = policy_result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Meal Policy not found")

    user_result = db.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    created_at_naive_kst = (parse_created_at_kst_to_utc(created_at) if created_at is not None else utc_now()).astimezone(KST).replace(tzinfo=None)
    new_log = MealLog(
        user_id=user_id,
        policy_id=policy_id,
        guest_count=guest_count,
        status="SERVED",
        path="MANUAL",
        final_price=policy.base_price,
        created_at=created_at_naive_kst
    )
    db.add(new_log)
    db.flush()
    
    record_audit_log(
        db, operator_id, "CREATE", "meal_logs", new_log.id,
        after_value={
            "user_id": user_id,
            "policy_id": policy_id,
            "guest_count": guest_count,
            "path": "MANUAL"
        },
        reason=reason
    )
    
    db.commit()
    db.refresh(new_log)
    
    # 수동 등록은 DB만 저장. 프린터·경광등 없음. 대시보드 숫자 갱신용 이벤트만 송신.
    from app.api.websocket import manager
    background_tasks.add_task(manager.broadcast, {"type": "STATS_REFRESH", "data": {}})
    
    return new_log

@router.patch("/{log_id}/void", response_model=MealLogResponse)
def void_meal_log(
    log_id: int,
    reason: str,
    background_tasks: BackgroundTasks,
    operator_id: int = 1, # Placeholder
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealLog).where(MealLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Meal log not found")
    
    if log.is_void:
        raise HTTPException(status_code=400, detail="Log is already voided")
        
    log.is_void = True
    log.void_reason = reason
    log.void_operator_id = operator_id
    log.voided_at = utc_now()
    
    record_audit_log(
        db, operator_id, "VOID", "meal_logs", log.id,
        before_value={"is_void": False},
        after_value={"is_void": True, "void_reason": reason},
        reason="Admin voiding"
    )
    
    db.commit()
    db.refresh(log)
    
    # WebSocket Broadcast (실시간 갱신용)
    from app.api.websocket import manager
    background_tasks.add_task(
        manager.broadcast,
        {"type": "MEAL_LOG_VOIDED", "data": {"log_id": log.id}},
    )
    
    return log

@router.put("/{log_id}", response_model=MealLogResponse)
def update_raw_data(
    log_id: int,
    update_data: MealLogUpdate,
    operator_id: int = 1,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealLog).where(MealLog.id == log_id))
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
        policy_result = db.execute(select(MealPolicy).where(MealPolicy.id == update_data.policy_id))
        policy = policy_result.scalar_one_or_none()
        if policy:
            log.policy_id = update_data.policy_id
            log.final_price = policy.base_price
    if update_data.created_at is not None:
        log.created_at = (parse_created_at_kst_to_utc(update_data.created_at) or utc_now()).astimezone(KST).replace(tzinfo=None)
    if update_data.guest_count is not None: log.guest_count = update_data.guest_count
    
    record_audit_log(
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
    
    db.commit()
    db.refresh(log)
    return log

@router.delete("/{log_id}")
def delete_raw_data(
    log_id: int,
    operator_id: int = 1,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealLog).where(MealLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Meal log not found")
        
    record_audit_log(
        db, operator_id, "DELETE", "meal_logs", log.id,
        before_value={"id": log.id, "user_id": log.user_id},
        reason="Admin physical delete"
    )
    
    db.delete(log)
    db.commit()
    return {"message": "Deleted successfully"}
