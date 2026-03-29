from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, JSON, Boolean, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# 식당 운영 위탁사 관리자 (사원과 별도 테이블)
class CafeteriaAdmin(Base):
    __tablename__ = "cafeteria_admins"
    id = Column(Integer, primary_key=True, index=True)
    emp_no = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True) # Company Code
    name = Column(String(100), nullable=False)
    domain = Column(String(100), unique=True, index=True, nullable=True)
    config = Column(JSON, default={})
    
    users = relationship("User", back_populates="company", cascade="all, delete-orphan", passive_deletes=True)
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan", passive_deletes=True)
    policies = relationship("MealPolicy", back_populates="company", cascade="all, delete-orphan", passive_deletes=True)

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    code = Column(String(50), index=True) # Dept Code
    name = Column(String(100), nullable=False)
    
    company = relationship("Company", back_populates="departments")
    users = relationship("User", back_populates="department_ref")

class User(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    emp_no = Column(String(50), index=True)
    name = Column(String(100))
    
    social_provider = Column(String(20)) # kakao, naver, google, sms
    
    # PC Admin Role & Status
    status = Column(String(20), default="ACTIVE") # ACTIVE, LEAVE, RESIGNED
    resigned_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="users")
    department_ref = relationship("Department", back_populates="users")
    
    @property
    def department_name(self):
        return self.department_ref.name if self.department_ref else "N/A"
    meal_logs = relationship("MealLog", foreign_keys="[MealLog.user_id]", back_populates="user")
    voided_logs = relationship("MealLog", foreign_keys="[MealLog.void_operator_id]", back_populates="void_operator")

class MealPolicy(Base):
    __tablename__ = "meal_policies"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    meal_type = Column(String(20)) # breakfast, lunch, dinner
    start_time = Column(Time)
    end_time = Column(Time)
    base_price = Column(Integer, default=0)
    guest_price = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    company = relationship("Company", back_populates="policies")


class MealQrTerminal(Base):
    """QR 스캔 구역별 프린터·경광등 매핑. 스캔 문자열은 system_settings device 의 allowed_qr_entries 에서 id 로 연결."""
    __tablename__ = "meal_qr_terminals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="")  # 표시용 (예: 1번 구역)
    qr_auth_id = Column(Integer, unique=True, nullable=False, index=True)  # device.allowed_qr_entries[].id
    printer_enabled = Column(Boolean, default=False)
    printer_host = Column(String(100), default="")
    printer_port = Column(Integer, default=9100)
    printer_stored_image_number = Column(Integer, default=1)
    qlight_enabled = Column(Boolean, default=False)
    qlight_host = Column(String(100), default="")
    qlight_port = Column(Integer, default=20000)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MealLog(Base):
    __tablename__ = "meal_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    policy_id = Column(Integer, ForeignKey("meal_policies.id", ondelete="CASCADE"))
    guest_count = Column(Integer, default=0)
    status = Column(String(20)) # ARRIVED, SERVED

    path = Column(String(20), default="PWA") # PWA, MANUAL, QR
    qr_terminal_id = Column(Integer, ForeignKey("meal_qr_terminals.id", ondelete="SET NULL"), nullable=True)
    final_price = Column(Integer, default=0) # Price snapshot at creation
    
    is_void = Column(Boolean, default=False)
    void_reason = Column(String(255), nullable=True)
    void_operator_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    voided_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=False), server_default=func.now())  # 한국 시간(KST) 로컬 시각 그대로 저장
    
    user = relationship("User", foreign_keys=[user_id], back_populates="meal_logs")
    policy = relationship("MealPolicy")
    void_operator = relationship("User", foreign_keys=[void_operator_id], back_populates="voided_logs")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50)) # CREATE, UPDATE, DELETE, VOID, IMPORT
    target_table = Column(String(50))
    target_id = Column(Integer)
    before_value = Column(JSON, nullable=True)
    after_value = Column(JSON, nullable=True)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    operator = relationship("User")


class SystemSetting(Base):
    """키-값 형태 시스템 설정 (장치 설정 등). key='device' → 프린터/경광등 설정."""
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True, default=dict)
