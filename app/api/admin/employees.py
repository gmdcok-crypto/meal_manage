from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select, update, and_, or_, func
from app.core.database import get_db
from app.models.models import User, AuditLog
from app.schemas.schemas import UserResponse, UserCreate, UserUpdate
from .utils import record_audit_log
from typing import List, Optional
from datetime import datetime

router = APIRouter(tags=["employees"])

@router.get("", response_model=List[UserResponse])
async def list_employees(
    dept: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).options(joinedload(User.department_ref))
    filters = []
    if dept:
        filters.append(User.department_id == int(dept))
    if status:
        filters.append(User.status == status)
    
    # Exclude system admin from regular employee list
    filters.append(User.emp_no != "admin")
    if search:
        filters.append(or_(
            User.name.icontains(search),
            User.emp_no.icontains(search)
        ))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query.order_by(User.emp_no))
    return result.scalars().all()

@router.post("", response_model=UserResponse)
async def create_employee(
    user_in: UserCreate,
    operator_id: int = 1, # Placeholder for current user auth
    db: AsyncSession = Depends(get_db)
):
    # Check if emp_no already exists
    existing = await db.execute(select(User).where(User.emp_no == user_in.emp_no))
    existing_user = existing.scalar_one_or_none()

    if existing_user:
        if existing_user.status == "RESIGNED":
            # Re-register: update the resigned user (same emp_no, new company/dept/name)
            existing_user.status = "ACTIVE"
            existing_user.resigned_at = None
            existing_user.company_id = user_in.company_id
            existing_user.department_id = user_in.department_id
            existing_user.name = user_in.name
            existing_user.is_verified = False
            existing_user.password_hash = None
            await record_audit_log(
                db, operator_id, "UPDATE", "employees", existing_user.id,
                before_value={"status": "RESIGNED"},
                after_value=user_in.dict(),
                reason="Re-registration (was resigned)"
            )
            await db.commit()
            result = await db.execute(
                select(User).where(User.id == existing_user.id).options(joinedload(User.department_ref))
            )
            return result.scalar_one()
        else:
            raise HTTPException(status_code=400, detail="Employee number already exists")

    new_user = User(**user_in.dict())
    db.add(new_user)
    await db.flush() # Get ID

    await record_audit_log(
        db, operator_id, "CREATE", "employees", new_user.id,
        after_value=user_in.dict(),
        reason="Manual registration"
    )

    await db.commit()
    # Refresh with relationship
    result = await db.execute(
        select(User).where(User.id == new_user.id).options(joinedload(User.department_ref))
    )
    return result.scalar_one()

@router.put("/{user_id}", response_model=UserResponse)
async def update_employee(
    user_id: int,
    user_in: UserUpdate,
    operator_id: int = 1, # Placeholder
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    before_value = {c.name: getattr(user, c.name) for c in user.__table__.columns if c.name in user_in.dict(exclude_unset=True)}
    
    update_data = user_in.dict(exclude_unset=True)
    if update_data.get("status") == "RESIGNED" and user.status != "RESIGNED":
        update_data["resigned_at"] = datetime.now()
    elif update_data.get("status") == "ACTIVE" and user.status == "RESIGNED":
        update_data["resigned_at"] = None

    for key, value in update_data.items():
        setattr(user, key, value)
    
    await record_audit_log(
        db, operator_id, "UPDATE", "employees", user.id,
        before_value=before_value,
        after_value=update_data,
        reason="Admin update"
    )
    
    await db.commit()
    # Refresh with relationship
    result = await db.execute(
        select(User).where(User.id == user.id).options(joinedload(User.department_ref))
    )
    return result.scalar_one()

@router.delete("/{user_id}")
async def delete_employee_soft(
    user_id: int,
    permanent: bool = Query(False, description="True면 DB에서 완전 삭제"),
    operator_id: int = 1, # Placeholder
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")

    if permanent:
        # Hard delete: remove row from DB (same emp_no can be re-registered later)
        await record_audit_log(
            db, operator_id, "DELETE", "employees", user.id,
            before_value={"emp_no": user.emp_no, "name": user.name, "status": user.status},
            reason="Admin permanent delete"
        )
        await db.delete(user)
        await db.commit()
        return {"message": "Employee permanently deleted", "deleted": True}
    else:
        # Soft delete: mark as RESIGNED (default)
        before_status = user.status
        user.status = "RESIGNED"
        user.resigned_at = datetime.now()

        await record_audit_log(
            db, operator_id, "RESIGN", "employees", user.id,
            before_value={"status": before_status},
            after_value={"status": "RESIGNED"},
            reason="Admin delete action (soft)"
        )

        await db.commit()
        return {"message": "Employee marked as resigned"}

@router.post("/{user_id}/reset-device")
async def reset_device_auth(
    user_id: int,
    operator_id: int = 1, # Placeholder
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    user.is_verified = False
    user.password_hash = None
    
    await record_audit_log(
        db, operator_id, "RESET_DEVICE", "employees", user.id,
        before_value={},
        after_value={"is_verified": False, "password_hash": None},
        reason="Admin requested device reset"
    )
    
    await db.commit()
    return {"message": "기기 인증 상태가 초기화되었습니다."}
@router.post("/import")
async def import_employees_excel(
    file_content: bytes,
    company_id: int,
    operator_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    import pandas as pd
    from io import BytesIO
    from app.models.models import Department
    
    try:
        df = pd.read_excel(BytesIO(file_content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"엑셀 파일을 읽을 수 없습니다: {str(e)}")
    
    # Required columns: 사번, 성명, 부서명
    required_cols = ["사번", "성명", "부서명"]
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"필수 컬럼이 누락되었습니다: {col}")
    
    # 1. Get all existing departments for this company
    result = await db.execute(select(Department).where(Department.company_id == company_id))
    existing_depts = {d.name: d.id for d in result.scalars().all()}
    
    # 2. Get existing users by emp_no for skip/re-register
    result = await db.execute(select(User))
    all_users = result.scalars().all()
    users_by_emp_no = {u.emp_no: u for u in all_users}

    success_count = 0
    skip_count = 0
    reregister_count = 0
    new_depts_count = 0

    for _, row in df.iterrows():
        emp_no = str(row["사번"]).strip()
        name = str(row["성명"]).strip()
        dept_name = str(row["부서명"]).strip()

        # 3. Handle department (for both new and re-register)
        if dept_name not in existing_depts:
            new_dept = Department(company_id=company_id, code=dept_name, name=dept_name)
            db.add(new_dept)
            await db.flush()
            existing_depts[dept_name] = new_dept.id
            new_depts_count += 1
        dept_id = existing_depts[dept_name]

        existing_user = users_by_emp_no.get(emp_no)
        if existing_user:
            if existing_user.status == "RESIGNED":
                existing_user.status = "ACTIVE"
                existing_user.resigned_at = None
                existing_user.company_id = company_id
                existing_user.department_id = dept_id
                existing_user.name = name
                existing_user.is_verified = False
                existing_user.password_hash = None
                reregister_count += 1
                success_count += 1
            else:
                skip_count += 1
            continue

        # 4. Create new User
        new_user = User(
            emp_no=emp_no,
            name=name,
            department_id=dept_id,
            company_id=company_id,
            status="ACTIVE",
            is_verified=False
        )
        db.add(new_user)
        users_by_emp_no[emp_no] = new_user
        success_count += 1

    await db.commit()

    return {
        "success_count": success_count,
        "skip_count": skip_count,
        "reregister_count": reregister_count,
        "new_depts_count": new_depts_count,
        "message": f"성공: {success_count}건 (재등록: {reregister_count}건), 건너뜀(중복): {skip_count}건, 신규 부서: {new_depts_count}건"
    }
