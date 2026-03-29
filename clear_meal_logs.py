"""기존 식사 로그(meal_logs) 전부 삭제. 테스트 초기화용. 한 번만 실행."""
from sqlalchemy import delete
from app.core.database import SessionLocal
from app.models.models import MealLog


def clear_meal_logs():
    with SessionLocal() as session:
        result = session.execute(delete(MealLog))
        session.commit()
        print(f"meal_logs 삭제 완료: {result.rowcount}건")


if __name__ == "__main__":
    clear_meal_logs()
