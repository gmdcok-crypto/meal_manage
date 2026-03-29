from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from jose import jwt, JWTError
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.config import settings
from app.models.models import MealPolicy, User, MealLog
from app.schemas.schemas import MealPolicyResponse
from app.core.time_utils import utc_now, KST

router = APIRouter(prefix="/meal", tags=["meal"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/verify_device")


class QRScanBody(BaseModel):
    qr_data: Optional[str] = None  # 스캔한 QR 내용. 허용 목록 사용 시 필수


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    
    result = db.execute(
        select(User).options(joinedload(User.department_ref)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if user.status == "RESIGNED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="퇴사 처리된 사원은 식사 인증을 사용할 수 없습니다."
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="기기가 초기화되었거나 인증되지 않았습니다. 다시 로그인해 주세요."
        )
    return user

@router.get("/today", response_model=list[MealPolicyResponse])
def get_today_policies(db: Session = Depends(get_db)):
    # 금일 활성화된 식사 정책 조회
    result = db.execute(select(MealPolicy).where(MealPolicy.is_active == True))
    return result.scalars().all()

@router.post("/qr-scan")
def process_qr_scan(
    body: QRScanBody,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def _norm_qr(s):
        if s is None or not isinstance(s, str):
            return ""
        return s.strip().replace("\ufeff", "").replace("\r", "").replace("\n", "").strip()

    from app.api.admin.settings import coalesce_allowed_qr_entries, get_device_settings_from_db
    from app.api.admin.terminals import (
        count_terminals,
        find_terminal_by_qr,
        legacy_device_payload_from_settings,
        terminal_to_device_payload,
    )

    qr_val = _norm_qr(body.qr_data)
    n_terminals = count_terminals(db)
    qr_terminal_id = None
    device_payload = None

    if n_terminals > 0:
        # 터미널이 하나라도 있으면: 스캔 문자열이 인증 QR 목록의 code 와 일치하고, 해당 QR ID 를 쓰는 터미널이 있어야 함
        if not qr_val:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QR 코드를 스캔해 주세요.")
        terminal = find_terminal_by_qr(db, qr_val)
        if not terminal:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="등록되지 않은 QR입니다. 인증할 수 없습니다.")
        qr_terminal_id = terminal.id
        device_payload = terminal_to_device_payload(terminal, matched_scan=qr_val)
    else:
        # 레거시: 터미널 없음 — allowed_qr_entries 의 code 만 허용 (목록이 비어 있으면 검사 생략)
        device = get_device_settings_from_db(db)
        entries = coalesce_allowed_qr_entries(device)
        if len(entries) > 0:
            if not qr_val:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QR 코드를 스캔해 주세요.")
            allowed_set = {_norm_qr(e["code"]) for e in entries if e.get("code")}
            allowed_set.discard("")
            if qr_val not in allowed_set:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="등록되지 않은 QR입니다. 인증할 수 없습니다.")
        device_payload = legacy_device_payload_from_settings(device, matched_scan=qr_val)

    # 저장할 시각을 한 번 정한 뒤, 그 시각의 한국 시간(KST)으로 식사 종류(정책) 판단 및 로그 저장 (서버의 "지금"이 아닌 로그 시각 기준)
    event_kst = utc_now().astimezone(KST)
    log_time_kst = event_kst.time()

    # 식사 시간 범위 내에 있는 정책 검색 (로그에 저장될 시각 기준)
    result = db.execute(
        select(MealPolicy).where(
            and_(
                MealPolicy.is_active == True,
                MealPolicy.start_time <= log_time_kst,
                MealPolicy.end_time >= log_time_kst,
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
        qr_terminal_id=qr_terminal_id,
        final_price=policy.base_price,
        created_at=event_kst.replace(tzinfo=None)  # 한국 시간 로컬 시각 그대로 저장 (naive)
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    # WebSocket Broadcast (실시간 갱신 + PC 앱에서 프린터/경광등 신호용)
    from app.api.websocket import manager
    meal_type_label = {"breakfast": "조식", "lunch": "중식", "dinner": "석식"}.get(
        (policy.meal_type or "").lower(), (policy.meal_type or "번외")
    )
    date_time_str = event_kst.strftime("%Y-%m-%d %H:%M") if event_kst else ""
    background_tasks.add_task(
        manager.broadcast,
        {
            "type": "MEAL_LOG_CREATED",
            "data": {
                "log_id": new_log.id,
                "emp_no": current_user.emp_no,
                "name": current_user.name,
                "meal_type_label": meal_type_label,
                "date_time_str": date_time_str,
                "device": device_payload,
            },
        },
    )
    
    return {
        "status": "success",
        "message": "식수 인증이 완료되었습니다.",
        "log_id": new_log.id,
        "auth_time": (new_log.created_at.strftime("%H:%M:%S") if new_log.created_at else "00:00:00"),
        "meal_type": (policy.meal_type if policy else "") or "",
        "user": {
            "name": current_user.name,
            "emp_no": current_user.emp_no,
            "dept_name": current_user.department_name
        }
    }

@router.post("/pre-check")
def pre_check_meal(policy_id: int, guest_count: int = 0):
    # 식사 전 사전 인증 처리
    return {"status": "ARRIVED_PRE_CHECKED", "message": "Pre-check completed"}
