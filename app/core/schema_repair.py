"""create_all은 새 테이블만 만들고 기존 테이블에 컬럼을 추가하지 않음.
배포 DB가 코드보다 오래된 경우 누락 컬럼으로 SELECT 시 500이 나므로 기동 시 보강."""
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _mysql_is_duplicate_column(msg: str) -> bool:
    m = msg.lower()
    return "duplicate" in m or "1060" in m or "already exists" in m


def _mysql_try_ddl(conn, ddl: str, label: str) -> None:
    try:
        conn.execute(text(ddl))
        logger.info("Schema repair: %s", label)
    except Exception as e:
        if _mysql_is_duplicate_column(str(e)):
            return
        logger.warning("Schema repair %s: %s", label, e)


def _pg_try_ddl(conn, ddl: str, label: str) -> None:
    try:
        conn.execute(text(ddl))
        logger.info("Schema repair: %s", label)
    except Exception as e:
        logger.warning("Schema repair %s: %s", label, e)


def _sqlite_try_ddl(conn, ddl: str, label: str) -> None:
    try:
        conn.execute(text(ddl))
        logger.info("Schema repair: %s", label)
    except Exception as e:
        if "duplicate column" in str(e).lower():
            return
        logger.warning("Schema repair %s: %s", label, e)


def ensure_meal_logs_columns(engine: Engine) -> None:
    """ORM이 조회에 쓰는 meal_logs 컬럼이 예전 DB에 없으면 추가."""
    with engine.begin() as conn:
        dialect = conn.dialect.name

        if dialect == "mysql":
            for ddl, label in (
                ("ALTER TABLE meal_logs ADD COLUMN path VARCHAR(20) DEFAULT 'PWA'", "meal_logs.path"),
                ("ALTER TABLE meal_logs ADD COLUMN qr_terminal_id INT NULL", "meal_logs.qr_terminal_id"),
                ("ALTER TABLE meal_logs ADD COLUMN final_price INT DEFAULT 0", "meal_logs.final_price"),
                ("ALTER TABLE meal_logs ADD COLUMN is_void TINYINT(1) DEFAULT 0", "meal_logs.is_void"),
                ("ALTER TABLE meal_logs ADD COLUMN void_reason VARCHAR(255) NULL", "meal_logs.void_reason"),
                ("ALTER TABLE meal_logs ADD COLUMN void_operator_id INT NULL", "meal_logs.void_operator_id"),
                ("ALTER TABLE meal_logs ADD COLUMN voided_at DATETIME NULL", "meal_logs.voided_at"),
            ):
                _mysql_try_ddl(conn, ddl, label)

        elif dialect == "postgresql":
            for ddl, label in (
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS path VARCHAR(20) DEFAULT 'PWA'",
                    "meal_logs.path",
                ),
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS qr_terminal_id INTEGER NULL",
                    "meal_logs.qr_terminal_id",
                ),
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS final_price INTEGER DEFAULT 0",
                    "meal_logs.final_price",
                ),
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS is_void BOOLEAN DEFAULT FALSE",
                    "meal_logs.is_void",
                ),
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS void_reason VARCHAR(255) NULL",
                    "meal_logs.void_reason",
                ),
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS void_operator_id INTEGER NULL",
                    "meal_logs.void_operator_id",
                ),
                (
                    "ALTER TABLE meal_logs ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ NULL",
                    "meal_logs.voided_at",
                ),
            ):
                _pg_try_ddl(conn, ddl, label)

        elif dialect == "sqlite":
            for ddl, label in (
                ("ALTER TABLE meal_logs ADD COLUMN path VARCHAR(20) DEFAULT 'PWA'", "meal_logs.path"),
                ("ALTER TABLE meal_logs ADD COLUMN qr_terminal_id INTEGER NULL", "meal_logs.qr_terminal_id"),
                ("ALTER TABLE meal_logs ADD COLUMN final_price INTEGER DEFAULT 0", "meal_logs.final_price"),
                ("ALTER TABLE meal_logs ADD COLUMN is_void INTEGER DEFAULT 0", "meal_logs.is_void"),
                ("ALTER TABLE meal_logs ADD COLUMN void_reason VARCHAR(255) NULL", "meal_logs.void_reason"),
                ("ALTER TABLE meal_logs ADD COLUMN void_operator_id INTEGER NULL", "meal_logs.void_operator_id"),
                ("ALTER TABLE meal_logs ADD COLUMN voided_at DATETIME NULL", "meal_logs.voided_at"),
            ):
                _sqlite_try_ddl(conn, ddl, label)
