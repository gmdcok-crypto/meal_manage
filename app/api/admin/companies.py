from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import Company, AuditLog
from app.schemas.schemas import CompanyCreate, CompanyUpdate, CompanyResponse
from app.api.admin.utils import record_audit_log
from typing import List

router = APIRouter()

@router.get("", response_model=List[CompanyResponse])
def get_companies(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    result = db.execute(select(Company))
    return result.scalars().all()

@router.post("", response_model=CompanyResponse)
def create_company(company: CompanyCreate, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    # Check if code already exists
    existing = db.execute(select(Company).where(Company.code == company.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Company code already exists")
    
    new_company = Company(**company.dict())
    db.add(new_company)
    db.flush()
    
    record_audit_log(
        db, 1, "CREATE", "companies", new_company.id, 
        after_value=company.dict(), reason="Admin created company"
    )
    db.commit()
    db.refresh(new_company)
    return new_company

@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, company_in: CompanyUpdate, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    result = db.execute(select(Company).where(Company.id == company_id))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    before_value = {
        "code": db_company.code,
        "name": db_company.name,
        "domain": db_company.domain
    }
    
    update_data = company_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_company, field, value)
    
    record_audit_log(
        db, 1, "UPDATE", "companies", company_id,
        before_value=before_value, after_value=update_data,
        reason="Admin updated company"
    )
    db.commit()
    db.refresh(db_company)
    return db_company

@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    result = db.execute(select(Company).where(Company.id == company_id))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for linked entities (simplified)
    # In a real app, you might want soft delete or strict foreign key checks
    
    record_audit_log(
        db, 1, "DELETE", "companies", company_id,
        before_value={"code": db_company.code, "name": db_company.name},
        reason="Admin deleted company"
    )
    db.delete(db_company)
    db.commit()
    return {"status": "success"}
