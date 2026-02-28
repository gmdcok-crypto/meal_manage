"""
로컬 DB 데이터를 Railway DB로 복사합니다.

사용법:
  1. Railway MySQL 연결 정보를 환경변수에 설정:
     set RAILWAY_DATABASE_URL=mysql+aiomysql://사용자:비밀번호@호스트:3306/railway
  2. 로컬 DB는 기본값(app/core/config.py) 또는:
     set LOCAL_DATABASE_URL=mysql+aiomysql://root:비밀번호@localhost:3306/meal_db
  3. Railway 쪽에 테이블이 있어야 함 (없으면 먼저 repair_db.py를 RAILWAY_DATABASE_URL로 실행)
  4. 실행:
     python migrate_to_railway.py
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 환경변수: 로컬=원본, Railway=대상
LOCAL_URL = os.environ.get("LOCAL_DATABASE_URL") or "mysql+aiomysql://root:700312ok!@localhost:3306/meal_db"
RAILWAY_URL = os.environ.get("RAILWAY_DATABASE_URL")
if not RAILWAY_URL:
    print("오류: RAILWAY_DATABASE_URL 환경변수를 설정하세요.")
    print("예: set RAILWAY_DATABASE_URL=mysql+aiomysql://user:pass@host:3306/railway")
    exit(1)

# FK 순서대로 복사 (부모 -> 자식)
TABLES = ["companies", "departments", "users", "meal_policies", "meal_logs", "audit_logs"]


async def copy_table(local_conn, rail_conn, table):
    result = await local_conn.execute(text(f"SELECT * FROM {table}"))
    rows = result.fetchall()
    if not rows:
        print(f"  {table}: 건너뜀 (0건)")
        return 0
    cols = list(result.keys())
    col_list = ", ".join(cols)
    placeholders = ", ".join([f":{c}" for c in cols])
    insert_sql = text(f"INSERT IGNORE INTO {table} ({col_list}) VALUES ({placeholders})")
    count = 0
    for row in rows:
        try:
            await rail_conn.execute(insert_sql, dict(zip(cols, row)))
            count += 1
        except Exception as e:
            print(f"  {table} 행 오류: {e}")
    print(f"  {table}: {count}건 복사")
    return count


async def run():
    local_engine = create_async_engine(LOCAL_URL)
    rail_engine = create_async_engine(RAILWAY_URL)
    print("로컬 DB 연결:", LOCAL_URL.split("@")[-1] if "@" in LOCAL_URL else LOCAL_URL)
    print("Railway DB 연결:", RAILWAY_URL.split("@")[-1].split("/")[0] if "@" in RAILWAY_URL else "***")
    print()

    async with local_engine.connect() as local_conn:
        async with rail_engine.begin() as rail_conn:
            await rail_conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            try:
                for table in TABLES:
                    await copy_table(local_conn, rail_conn, table)
            finally:
                await rail_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    await local_engine.dispose()
    await rail_engine.dispose()
    print("\n완료. PC 앱에서 Railway 데이터를 확인하세요.")


if __name__ == "__main__":
    asyncio.run(run())
