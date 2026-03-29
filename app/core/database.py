from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from .config import settings

try:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )
except Exception as e:
    import sys
    u = settings.DATABASE_URL
    masked = u[:25] + "***" + u[-15:] if len(u) > 45 else "***"
    print(f"[DB] Engine creation failed: {e}", file=sys.stderr)
    print(f"[DB] DATABASE_URL (masked): {masked}", file=sys.stderr)
    raise

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
