import asyncio
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import engine, Base, SessionLocal
from app.models.models import User
from app.core.config import settings

async def repair():
    # 1. Create database if not exists using aiomysql
    root_url = settings.DATABASE_URL.rsplit("/", 1)[0] # get mysql+aiomysql://root:pass@localhost:3306
    db_name = settings.DATABASE_URL.rsplit("/", 1)[1]  # get meal_db
    
    # Connect to the server without a database
    temp_engine = create_async_engine(root_url)
    async with temp_engine.connect() as conn:
        await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
        await conn.commit()
        print(f"Database '{db_name}' ensured.")
    await temp_engine.dispose()

    # 2. Re-initialize async engine to make sure it picks up the new DB
    async_engine = create_async_engine(settings.DATABASE_URL)
    
    async with async_engine.begin() as conn:
        # 3. Ensure tables exist (recreates users table if deleted)
        await conn.run_sync(Base.metadata.create_all)
        print("Schema ensured (tables created/verified).")
        
        # 4. Check and add/remove columns for data consistency
        # Add 'code' to companies if missing
        try:
            await conn.execute(text("ALTER TABLE companies ADD COLUMN code VARCHAR(50)"))
            print("Ensured 'code' column in companies")
        except: pass

        # Ensure 'department_id' in users
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN department_id INTEGER"))
            print("Ensured 'department_id' column in users")
        except: pass

        # Ensure 'is_verified' in users
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
            print("Ensured 'is_verified' column in users")
        except: pass

        # Ensure 'password_hash' in users
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            print("Ensured 'password_hash' column in users")
        except: pass

        # Ensure 'policy_id' in meal_logs (rename menu_id if exists)
        try:
            result = await conn.execute(text("DESCRIBE meal_logs"))
            columns = [col[0] for col in result.fetchall()]
            if "menu_id" in columns and "policy_id" not in columns:
                await conn.execute(text("ALTER TABLE meal_logs CHANGE COLUMN menu_id policy_id INT(11)"))
                print("Migrated 'menu_id' to 'policy_id' in meal_logs")
            elif "policy_id" not in columns:
                await conn.execute(text("ALTER TABLE meal_logs ADD COLUMN policy_id INT(11)"))
                print("Added 'policy_id' column to meal_logs")
        except Exception as e:
            print(f"Error ensuring 'policy_id' in meal_logs: {e}")

        # 5. Ensure ON DELETE CASCADE for all foreign keys
        print("\nOptimizing Foreign Key constraints (ON DELETE CASCADE)...")
        fk_configs = [
            ("departments", "company_id", "companies", "CASCADE"),
            ("users", "company_id", "companies", "CASCADE"),
            ("users", "department_id", "departments", "CASCADE"),
            ("meal_policies", "company_id", "companies", "CASCADE"),
            ("meal_logs", "user_id", "users", "CASCADE"),
            ("meal_logs", "policy_id", "meal_policies", "CASCADE"),
            ("meal_logs", "void_operator_id", "users", "SET NULL"),
            ("audit_logs", "operator_id", "users", "SET NULL")
        ]

        for table, col, ref_table, on_delete in fk_configs:
            try:
                # Find existing FK name
                fk_query = text(f"""
                    SELECT CONSTRAINT_NAME 
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table 
                    AND COLUMN_NAME = :col AND REFERENCED_TABLE_NAME IS NOT NULL
                """)
                res = await conn.execute(fk_query, {"db": db_name, "table": table, "col": col})
                fk_name = res.scalar()
                
                if fk_name:
                    await conn.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {fk_name}"))
                    print(f"  Dropped old FK {fk_name} on {table}({col})")
                
                # Add new FK with CASCADE/SET NULL
                new_fk_name = f"fk_{table}_{col}_{ref_table}"
                await conn.execute(text(f"""
                    ALTER TABLE {table} 
                    ADD CONSTRAINT {new_fk_name} 
                    FOREIGN KEY ({col}) REFERENCES {ref_table}(id) 
                    ON DELETE {on_delete}
                """))
                print(f"  Added Optimized FK {new_fk_name} (ON DELETE {on_delete})")
            except Exception as e:
                print(f"  Note: Skipped FK optimization for {table}({col}): {e}")

    # 5. Ensure admin user exists (re-add if table was wiped)
    async with async_sessionmaker(async_engine, expire_on_commit=False)() as db:
        try:
            from sqlalchemy import select
            res = await db.execute(select(User).where(User.emp_no == "admin"))
            if not res.scalar():
                db.add(User(
                    id=1, 
                    name="System Admin", 
                    emp_no="admin", 
                    status="ACTIVE",
                    social_provider="MANUAL"
                ))
                await db.commit()
                print("Created default admin user (admin)")
            else:
                print("Admin user already exists")
        except Exception as e:
            print(f"Error checking/creating admin user: {e}")
    
    await async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(repair())
