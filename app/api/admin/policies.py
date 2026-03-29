from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.core.database import get_db
from app.api.auth import get_current_admin
from app.models.models import MealPolicy, AuditLog, Company
from app.schemas.schemas import MealPolicyResponse, MealPolicyBase
from .utils import record_audit_log
from typing import List

router = APIRouter(tags=["policies"])

@router.get("", response_model=List[MealPolicyResponse])
def list_policies(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    result = db.execute(select(MealPolicy))
    return result.scalars().all()

@router.post("", response_model=MealPolicyResponse)
def create_policy(
    policy_in: MealPolicyBase,
    operator_id: int = 1, # Placeholder
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    # 유효한 회사 ID 요청
    company_res = db.execute(select(Company.id).limit(1))
    company_id = company_res.scalar()
    
    if not company_id:
        raise HTTPException(status_code=400, detail="등록된 회사가 없습니다. 먼저 회사를 등록해주세요.")

    new_policy = MealPolicy(**policy_in.dict(), company_id=company_id)
    db.add(new_policy)
    db.flush()
    
    # JSON 직렬화를 위해 time 객체를 문자열로 변환
    audit_data = policy_in.dict()
    for k, v in audit_data.items():
        if hasattr(v, 'isoformat') and not isinstance(v, str):
            audit_data[k] = v.isoformat()

    record_audit_log(
        db, operator_id, "CREATE", "meal_policies", new_policy.id,
        after_value=audit_data,
        reason="Initial policy setup"
    )
    
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.put("/{policy_id}", response_model=MealPolicyResponse)
def update_policy(
    policy_id: int,
    policy_in: MealPolicyBase,
    operator_id: int = 1, # Placeholder
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealPolicy).where(MealPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    before_value = {c.name: getattr(policy, c.name).isoformat() if hasattr(getattr(policy, c.name), 'isoformat') and not isinstance(getattr(policy, c.name), str) else getattr(policy, c.name) for c in policy.__table__.columns if c.name in policy_in.dict()}
    
    # JSON 직렬화를 위해 time 객체를 문자열로 변환
    after_value = policy_in.dict()
    for k, v in after_value.items():
        if hasattr(v, 'isoformat') and not isinstance(v, str):
            after_value[k] = v.isoformat()

    for key, value in policy_in.dict().items():
        setattr(policy, key, value)
        
    record_audit_log(
        db, operator_id, "UPDATE", "meal_policies", policy.id,
        before_value=before_value,
        after_value=after_value,
        reason="Policy update"
    )
    
    db.commit()
    db.refresh(policy)
    return policy

@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    operator_id: int = 1, # Placeholder
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = db.execute(select(MealPolicy).where(MealPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    record_audit_log(
        db, operator_id, "DELETE", "meal_policies", policy.id,
        before_value=None,
        after_value=None,
        reason="Policy deletion"
    )
    
    db.delete(policy)
    db.commit()
    
    return {"ok": True}
