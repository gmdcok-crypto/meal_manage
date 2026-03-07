"""기존 식사 로그(meal_logs) 전부 삭제. 테스트 초기화용. 한 번만 실행."""
import asyncio
from sqlalchemy import delete
from app.core.database import SessionLocal
from app.models.models import MealLog


async def clear_meal_logs():
    async with SessionLocal() as session:
        result = await session.execute(delete(MealLog))
        await session.commit()
        print(f"meal_logs 삭제 완료: {result.rowcount}건")


if __name__ == "__main__":
    asyncio.run(clear_meal_logs())
