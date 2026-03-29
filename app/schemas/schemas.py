from datetime import datetime, time, date, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer, field_validator

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

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def coerce_sql_time(cls, v):
        """MySQL TIME 등이 timedelta로 올 때 응답 직렬화 500 방지."""
        if v is None:
            return None
        if isinstance(v, time):
            return v
        if isinstance(v, timedelta):
            sec = int(v.total_seconds()) % 86400
            if sec < 0:
                sec += 86400
            h, rem = divmod(sec, 3600)
            m, s = divmod(rem, 60)
            return time(h, m, s)
        return v


class MealPolicyResponse(MealPolicyBase):
    id: int
    company_id: Optional[int] = None  # 레거시 행 NULL 허용 (필수 int면 ORM→스키마 검증 500)

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
    policy_id: Optional[int] = None  # 번외 등 DB NULL 허용 → 직렬화/보고서 조회 500 방지
    guest_count: int
    status: str
    path: str
    qr_terminal_id: Optional[int] = None
    qr_auth_id: Optional[int] = None
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
class AuthQrEntry(BaseModel):
    id: int
    code: str  # PWA 스캔 문자열과 전체 일치


class DeviceSettingsResponse(BaseModel):
    printer_enabled: bool = False
    printer_host: str = ""
    printer_port: int = 9100
    printer_stored_image_number: int = 1
    qlight_enabled: bool = False
    qlight_host: str = ""
    qlight_port: int = 20000
    allowed_qr_entries: List[AuthQrEntry] = []


class DeviceSettingsUpdate(BaseModel):
    printer_enabled: Optional[bool] = None
    printer_host: Optional[str] = None
    printer_port: Optional[int] = None
    printer_stored_image_number: Optional[int] = None
    qlight_enabled: Optional[bool] = None
    qlight_host: Optional[str] = None
    qlight_port: Optional[int] = None
    allowed_qr_entries: Optional[List[AuthQrEntry]] = None


# QR 터미널 (구역별 프린터·경광등)
class MealQrTerminalBase(BaseModel):
    name: str = ""
    qr_auth_id: int
    printer_enabled: bool = False
    printer_host: str = ""
    printer_port: int = 9100
    printer_stored_image_number: int = 1
    qlight_enabled: bool = False
    qlight_host: str = ""
    qlight_port: int = 20000
    is_active: bool = True
    sort_order: int = 0


class MealQrTerminalCreate(MealQrTerminalBase):
    pass


class MealQrTerminalUpdate(BaseModel):
    name: Optional[str] = None
    qr_auth_id: Optional[int] = None
    printer_enabled: Optional[bool] = None
    printer_host: Optional[str] = None
    printer_port: Optional[int] = None
    printer_stored_image_number: Optional[int] = None
    qlight_enabled: Optional[bool] = None
    qlight_host: Optional[str] = None
    qlight_port: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class MealQrTerminalResponse(MealQrTerminalBase):
    id: int

    class Config:
        from_attributes = True


# 프린터 / 경광등 각각 독립 테이블·API
class MealPrinterTerminalBase(BaseModel):
    name: str = ""
    qr_auth_id: int
    printer_host: str = ""
    printer_port: int = 9100
    printer_stored_image_number: int = 1
    is_active: bool = True
    sort_order: int = 0


class MealPrinterTerminalCreate(MealPrinterTerminalBase):
    pass


class MealPrinterTerminalUpdate(BaseModel):
    name: Optional[str] = None
    qr_auth_id: Optional[int] = None
    printer_host: Optional[str] = None
    printer_port: Optional[int] = None
    printer_stored_image_number: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class MealPrinterTerminalResponse(MealPrinterTerminalBase):
    id: int

    class Config:
        from_attributes = True


class MealQlightTerminalBase(BaseModel):
    name: str = ""
    qr_auth_id: int
    qlight_host: str = ""
    qlight_port: int = 20000
    is_active: bool = True
    sort_order: int = 0


class MealQlightTerminalCreate(MealQlightTerminalBase):
    pass


class MealQlightTerminalUpdate(BaseModel):
    name: Optional[str] = None
    qr_auth_id: Optional[int] = None
    qlight_host: Optional[str] = None
    qlight_port: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class MealQlightTerminalResponse(MealQlightTerminalBase):
    id: int

    class Config:
        from_attributes = True
