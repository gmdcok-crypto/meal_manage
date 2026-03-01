"""
사원(employees) 테이블의 모든 행을 재직(ACTIVE)으로 변경합니다.
status='ACTIVE', resigned_at=NULL 로 업데이트합니다.

사용법:
  - Railway 등 실제 사원 데이터가 있는 DB를 쓰려면 DATABASE_URL을 해당 DB로 설정한 뒤 실행.
  - 예: set MEAL_API_BASE_URL=... 후, DB URL이 .env 등에 있으면
        python set_employees_active.py

또는 DB 관리 툴에서 직접 SQL 실행:
  UPDATE employees SET status = 'ACTIVE', resigned_at = NULL;
"""
import asyncio
from sqlalchemy import update
from app.core.database import SessionLocal
from app.models.models import User


async def main():
    async with SessionLocal() as session:
        result = await session.execute(
            update(User).values(status="ACTIVE", resigned_at=None)
        )
        await session.commit()
        print(f"모든 사원을 재직(ACTIVE)으로 변경했습니다. (영향 행 수: {result.rowcount})")


if __name__ == "__main__":
    asyncio.run(main())
