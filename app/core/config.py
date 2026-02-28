from pydantic_settings import BaseSettings
from pydantic import field_validator

def _normalize_database_url(url: str) -> str:
    """공백/줄바꿈 제거, mysql:// → mysql+aiomysql:// 변환"""
    u = (url or "").strip().split("\n")[0].strip()
    if u.startswith("mysql://") and not u.startswith("mysql+aiomysql://"):
        u = "mysql+aiomysql://" + u[len("mysql://"):]
    return u

class Settings(BaseSettings):
    PROJECT_NAME: str = "PWA Meal Auth System"
    
    # Database
    DATABASE_URL: str = "mysql+aiomysql://root:700312ok!@localhost:3306/meal_db"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        return _normalize_database_url(v) if isinstance(v, str) else v
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-it-in-production"
    ALGORITHM: str = "HS256"
    # JWT: 인증된 사원은 기간 관계없이 2차 인증 없이 패스. 사원관리에서 초기화(X)한 경우에만 재인증 필요.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365 * 10  # 10년 (초기화 시 is_verified=False로 403 되어 재로그인 유도)
    
    # Social Auth (Placeholders)
    KAKAO_CLIENT_ID: str = ""
    NAVER_CLIENT_ID: str = ""
    GOOGLE_CLIENT_ID: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
