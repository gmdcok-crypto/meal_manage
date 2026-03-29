from sqlalchemy import inspect
from app.core.database import engine


def check():
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        print(f"Existing tables: {tables}")

        expected_tables = ["companies", "departments", "employees", "meal_policies", "meal_logs"]
        for t in expected_tables:
            if t not in tables:
                print(f"MISSING TABLE: {t}")


if __name__ == "__main__":
    check()
