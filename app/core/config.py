from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PWA Meal Auth System"
    
    # Database
    DATABASE_URL: str = "mysql+aiomysql://root:700312ok!@localhost:3306/meal_db"
    
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
