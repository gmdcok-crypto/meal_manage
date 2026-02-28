from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AuditLog, User

async def record_audit_log(
    db: AsyncSession,
    operator_id: int,
    action: str,
    target_table: str,
    target_id: int,
    before_value: dict = None,
    after_value: dict = None,
    reason: str = None
):
    # Verify operator exists to avoid FK error
    try:
        op_check = await db.execute(select(User).where(User.id == operator_id))
        if op_check.scalar_one_or_none() is None:
            operator_id = None  # Fallback to null if user doesn't exist
    except Exception:
        operator_id = None

    audit_log = AuditLog(
        operator_id=operator_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        before_value=before_value,
        after_value=after_value,
        reason=reason
    )
    db.add(audit_log)
    # Note: We assume the caller will commit the transaction
