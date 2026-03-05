from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings

try:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,   # 사용 전 연결 살아있는지 확인 → 끊긴 연결 재사용 방지
        pool_recycle=300,      # 5분마다 연결 갱신 (DB idle timeout 전에 재사용)
    )
except Exception as e:
    import sys
    u = settings.DATABASE_URL
    masked = u[:25] + "***" + u[-15:] if len(u) > 45 else "***"
    print(f"[DB] Engine creation failed: {e}", file=sys.stderr)
    print(f"[DB] DATABASE_URL (masked): {masked}", file=sys.stderr)
    raise

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session
