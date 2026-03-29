from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator

def _normalize_database_url(url: str) -> str:
    """공백/줄바꿈 제거. PyMySQL URL → mysql+pymysql:// 로 통일 (순수 Python, Railway 빌드용).

    SQLAlchemy `mariadb+pymysql` 방언은 서버가 MariaDB 계열인지 검사하는데, MySQL 8/9(예: 9.4.0)이면
    \"MySQL version … is not a MariaDB variant\" 로 연결이 실패할 수 있음.
    `mysql+pymysql` 은 MySQL·MariaDB 서버 모두에 동일하게 사용 가능.
    """
    u = (url or "").strip().split("\n")[0].strip()
    if u.startswith("mysql://") and "+" not in u.split("://", 1)[0]:
        u = "mysql+pymysql://" + u[len("mysql://") :]
    elif u.startswith("mysql+aiomysql://"):
        u = "mysql+pymysql://" + u[len("mysql+aiomysql://") :]
    elif u.startswith("mysql+asyncmy://"):
        u = "mysql+pymysql://" + u[len("mysql+asyncmy://") :]
    elif u.startswith("mariadb+mariadbconnector://"):
        u = "mysql+pymysql://" + u[len("mariadb+mariadbconnector://") :]
    elif u.startswith("mariadb+pymysql://"):
        u = "mysql+pymysql://" + u[len("mariadb+pymysql://") :]
    # 이미 mysql+pymysql:// 이면 그대로
    return u

_DEFAULT_DATABASE_URL = "mysql+pymysql://root:700312ok!@localhost:3306/meal_db"
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
    
    # 식권 프린터 (빅솔론). 비어 있으면 인쇄 생략
    PRINTER_HOST: str = ""
    PRINTER_PORT: int = 9100
    PRINTER_STORED_IMAGE_NUMBER: int = 1
    # 경광등 (Q라이트). DB 장치 설정에서 우선 사용
    QLIGHT_HOST: str = ""
    QLIGHT_PORT: int = 20000
    
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
