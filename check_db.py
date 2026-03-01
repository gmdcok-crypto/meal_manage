import asyncio
from sqlalchemy import inspect
from app.core.database import engine, Base
from app.models.models import User, Company, Department, MealPolicy, MealLog

async def check():
    async with engine.connect() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        
        tables = await conn.run_sync(get_tables)
        print(f"Existing tables: {tables}")
        
        expected_tables = ["companies", "departments", "employees", "meal_policies", "meal_logs"]
        for t in expected_tables:
            if t not in tables:
                print(f"MISSING TABLE: {t}")

if __name__ == "__main__":
    asyncio.run(check())
