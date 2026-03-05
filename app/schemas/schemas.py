from datetime import datetime, time, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer

from app.core.time_utils import utc_to_kst_str

# User Schemas
class UserBase(BaseModel):
    emp_no: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    is_verified: bool = False

class UserCreate(UserBase):
    company_id: int
    social_provider: Optional[str] = "MANUAL"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[int] = None
    status: Optional[str] = None


class AdminCreate(BaseModel):
    emp_no: str
    name: str


class AdminUpdate(BaseModel):
    name: Optional[str] = None


class CafeteriaAdminResponse(BaseModel):
    """식당관리(위탁사 운영자) 응답. PC 관리자 메뉴용."""
    id: int
    emp_no: str
    name: str
    is_verified: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int
    company_id: Optional[int] = None
    status: Optional[str] = None
    department_name: Optional[str] = None
    created_at: Optional[datetime] = None
    resigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Meal Policy Schemas (GET /policies 등에서 사용, DB NULL 허용으로 500 방지)
class MealPolicyBase(BaseModel):
    meal_type: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    base_price: Optional[int] = 0
    guest_price: Optional[int] = 0
    is_active: bool = True

class MealPolicyResponse(MealPolicyBase):
    id: int
    company_id: int
    
    class Config:
        from_attributes = True

# Meal Schemas

class MealLogCreate(BaseModel):
    policy_id: int
    guest_count: int = 0
    path: str = "PWA"

class MealLogResponse(BaseModel):
    id: int
    user_id: int
    policy_id: int
    guest_count: int
    status: str
    path: str
    final_price: int
    is_void: bool
    void_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_serializer("created_at")
    def serialize_created_at(self, dt: Optional[datetime]) -> str:
        return utc_to_kst_str(dt) or ""

    class Config:
        from_attributes = True

class MealLogAdminDetail(MealLogResponse):
    user: Optional[UserResponse] = None
    policy: Optional[MealPolicyResponse] = None
    void_operator: Optional[UserResponse] = None
    void_reason: Optional[str] = None

class MealLogUpdate(BaseModel):
    created_at: Optional[datetime] = None
    user_id: Optional[int] = None
    policy_id: Optional[int] = None
    guest_count: Optional[int] = None
    reason: Optional[str] = None

# Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: int
    operator_id: Optional[int] = None
    action: str
    target_table: str
    target_id: int
    before_value: Optional[dict] = None
    after_value: Optional[dict] = None
    reason: Optional[str] = None
    created_at: datetime
    operator: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Dashboard Schemas
class DashboardStats(BaseModel):
    date: date
    meal_type: str
    total_count: int
    employee_count: int
    guest_count: int
    exception_count: int
    meal_summaries: List[dict]

# Company Schemas
class CompanyBase(BaseModel):
    code: str
    name: str
    domain: Optional[str] = None
    config: Optional[dict] = {}

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    domain: Optional[str] = None
    config: Optional[dict] = None

class CompanyResponse(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True

# Department Schemas
class DepartmentBase(BaseModel):
    company_id: int
    code: str
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    company_id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None

class DepartmentResponse(DepartmentBase):
    id: int
    
    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

class VerifyDeviceRequest(BaseModel):
    emp_no: str
    name: str
    password: Optional[str] = ""  # 최초 인증 시 필수, 재로그인 시 사용


# 장치 설정 (프린터·경광등·허용 QR) - PC 앱 설정 메뉴용
class DeviceSettingsResponse(BaseModel):
    printer_enabled: bool = False
    printer_host: str = ""
    printer_port: int = 9100
    printer_stored_image_number: int = 1
    qlight_enabled: bool = False
    qlight_host: str = ""
    qlight_port: int = 20000
    allowed_qr_list: List[str] = []  # 비어 있으면 모든 QR 허용, 있으면 목록에 있는 QR만 인증


class DeviceSettingsUpdate(BaseModel):
    printer_enabled: Optional[bool] = None
    printer_host: Optional[str] = None
    printer_port: Optional[int] = None
    printer_stored_image_number: Optional[int] = None
    qlight_enabled: Optional[bool] = None
    qlight_host: Optional[str] = None
    qlight_port: Optional[int] = None
    allowed_qr_list: Optional[List[str]] = None
