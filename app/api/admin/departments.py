from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.core.database import get_db
from app.models.models import Department, AuditLog
from app.schemas.schemas import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.api.admin.utils import record_audit_log
from typing import List, Optional

router = APIRouter()

@router.get("", response_model=List[DepartmentResponse])
async def get_departments(company_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    query = select(Department)
    if company_id:
        query = query.where(Department.company_id == company_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=DepartmentResponse)
async def create_department(dept: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    # Check if code already exists within the company
    existing = await db.execute(
        select(Department).where(
            Department.company_id == dept.company_id,
            Department.code == dept.code
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Department code already exists for this company")
    
    new_dept = Department(**dept.dict())
    db.add(new_dept)
    await db.flush()
    
    await record_audit_log(
        db, 1, "CREATE", "departments", new_dept.id,
        after_value=dept.dict(), reason="Admin created department"
    )
    await db.commit()
    await db.refresh(new_dept)
    return new_dept

@router.patch("/{dept_id}", response_model=DepartmentResponse)
async def update_department(dept_id: int, dept_in: DepartmentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    db_dept = result.scalar_one_or_none()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    before_value = {
        "company_id": db_dept.company_id,
        "code": db_dept.code,
        "name": db_dept.name
    }
    
    update_data = dept_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_dept, field, value)
    
    await record_audit_log(
        db, 1, "UPDATE", "departments", dept_id,
        before_value=before_value, after_value=update_data,
        reason="Admin updated department"
    )
    await db.commit()
    await db.refresh(db_dept)
    return db_dept

@router.delete("/{dept_id}")
async def delete_department(dept_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    db_dept = result.scalar_one_or_none()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    await record_audit_log(
        db, 1, "DELETE", "departments", dept_id,
        before_value={"code": db_dept.code, "name": db_dept.name},
        reason="Admin deleted department"
    )
    await db.delete(db_dept)
    await db.commit()
    return {"status": "success"}
