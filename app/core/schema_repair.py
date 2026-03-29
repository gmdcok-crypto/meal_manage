"""create_all은 새 테이블만 만들고 기존 테이블에 컬럼을 추가하지 않음.
배포 DB가 코드보다 오래된 경우 누락 컬럼으로 SELECT 시 500이 나므로 기동 시 보강."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def ensure_meal_logs_columns(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        dialect = conn.dialect.name

        if dialect == "mysql":
            try:
                await conn.execute(
                    text("ALTER TABLE meal_logs ADD COLUMN qr_terminal_id INT NULL")
                )
                logger.info("Schema repair: added meal_logs.qr_terminal_id")
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "1060" in err or "already exists" in err:
                    return
                logger.warning("Schema repair meal_logs.qr_terminal_id: %s", e)

        elif dialect == "postgresql":
            try:
                await conn.execute(
                    text(
                        "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS qr_terminal_id INTEGER NULL"
                    )
                )
                logger.info("Schema repair: ensured meal_logs.qr_terminal_id")
            except Exception as e:
                logger.warning("Schema repair meal_logs.qr_terminal_id: %s", e)

        elif dialect == "sqlite":
            try:
                await conn.execute(
                    text("ALTER TABLE meal_logs ADD COLUMN qr_terminal_id INTEGER NULL")
                )
                logger.info("Schema repair: added meal_logs.qr_terminal_id (sqlite)")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    return
                logger.warning("Schema repair meal_logs.qr_terminal_id: %s", e)
