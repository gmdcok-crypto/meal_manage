from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator

def _normalize_database_url(url: str) -> str:
    """공백/줄바꿈 제거, mysql:// → mysql+aiomysql:// 변환"""
    u = (url or "").strip().split("\n")[0].strip()
    if u.startswith("mysql://") and not u.startswith("mysql+aiomysql://"):
        u = "mysql+aiomysql://" + u[len("mysql://"):]
    return u

_DEFAULT_DATABASE_URL = "mysql+aiomysql://root:700312ok!@localhost:3306/meal_db"
_DEFAULT_SECRET_KEY = "your-secret-key-change-it-in-production"

class Settings(BaseSettings):
    PROJECT_NAME: str = "PWA Meal Auth System"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = _DEFAULT_DATABASE_URL
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        return _normalize_database_url(v) if isinstance(v, str) else v
    
    # JWT
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    # JWT: 인증된 사원은 기간 관계없이 2차 인증 없이 패스. 사원관리에서 초기화(X)한 경우에만 재인증 필요.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365 * 10  # 10년 (초기화 시 is_verified=False로 403 되어 재로그인 유도)
    
    # Social Auth (Placeholders)
    KAKAO_CLIENT_ID: str = ""
    NAVER_CLIENT_ID: str = ""
    GOOGLE_CLIENT_ID: str = ""
    
    @model_validator(mode="after")
    def require_secrets_in_production(self):
        if getattr(self, "ENV", "development").lower() in ("production", "prod"):
            if self.DATABASE_URL == _DEFAULT_DATABASE_URL:
                raise ValueError("운영 환경에서는 DATABASE_URL 환경 변수를 설정해야 합니다.")
            if self.SECRET_KEY == _DEFAULT_SECRET_KEY:
                raise ValueError("운영 환경에서는 SECRET_KEY 환경 변수를 설정해야 합니다.")
        return self

    class Config:
        env_file = ".env"

settings = Settings()
