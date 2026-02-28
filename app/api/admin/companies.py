from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.core.database import get_db
from app.models.models import Company, AuditLog
from app.schemas.schemas import CompanyCreate, CompanyUpdate, CompanyResponse
from app.api.admin.utils import record_audit_log
from typing import List

router = APIRouter()

@router.get("", response_model=List[CompanyResponse])
async def get_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company))
    return result.scalars().all()

@router.post("", response_model=CompanyResponse)
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    # Check if code already exists
    existing = await db.execute(select(Company).where(Company.code == company.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Company code already exists")
    
    new_company = Company(**company.dict())
    db.add(new_company)
    await db.flush()
    
    await record_audit_log(
        db, 1, "CREATE", "companies", new_company.id, 
        after_value=company.dict(), reason="Admin created company"
    )
    await db.commit()
    await db.refresh(new_company)
    return new_company

@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(company_id: int, company_in: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
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
    
    await record_audit_log(
        db, 1, "UPDATE", "companies", company_id,
        before_value=before_value, after_value=update_data,
        reason="Admin updated company"
    )
    await db.commit()
    await db.refresh(db_company)
    return db_company

@router.delete("/{company_id}")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for linked entities (simplified)
    # In a real app, you might want soft delete or strict foreign key checks
    
    await record_audit_log(
        db, 1, "DELETE", "companies", company_id,
        before_value={"code": db_company.code, "name": db_company.name},
        reason="Admin deleted company"
    )
    await db.delete(db_company)
    await db.commit()
    return {"status": "success"}
