"""DB 생성·스키마 보강 (MariaDB 공식 Connector / 동기 SQLAlchemy)."""
from sqlalchemy import text, create_engine, select
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.models import User
from app.core.config import settings


def repair():
    root_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    db_name = settings.DATABASE_URL.rsplit("/", 1)[1]

    temp_engine = create_engine(root_url)
    with temp_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
        conn.commit()
        print(f"Database '{db_name}' ensured.")
    temp_engine.dispose()

    sync_engine = create_engine(settings.DATABASE_URL)

    with sync_engine.begin() as conn:
        try:
            res = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'users'"
                )
            )
            n = res.scalar()
            if n and int(n) > 0:
                conn.execute(text("RENAME TABLE users TO employees"))
                print("Migrated table: users -> employees")
        except Exception as e:
            print(f"Note: Migration users->employees: {e}")

        Base.metadata.create_all(bind=conn)
        print("Schema ensured (tables created/verified).")

        for ddl, label in (
            (
                """
                CREATE TABLE IF NOT EXISTS cafeteria_admins (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    emp_no VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    password_hash VARCHAR(255),
                    is_verified TINYINT(1) DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
                "cafeteria_admins",
            ),
            (
                """
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    `key` VARCHAR(50) NOT NULL UNIQUE,
                    value JSON
                )
            """,
                "system_settings",
            ),
            (
                """
                CREATE TABLE IF NOT EXISTS meal_qr_terminals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) DEFAULT '',
                    qr_code VARCHAR(512) NOT NULL,
                    printer_enabled TINYINT(1) DEFAULT 0,
                    printer_host VARCHAR(100) DEFAULT '',
                    printer_port INT DEFAULT 9100,
                    printer_stored_image_number INT DEFAULT 1,
                    qlight_enabled TINYINT(1) DEFAULT 0,
                    qlight_host VARCHAR(100) DEFAULT '',
                    qlight_port INT DEFAULT 20000,
                    is_active TINYINT(1) DEFAULT 1,
                    sort_order INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_meal_qr_terminals_qr (qr_code)
                )
            """,
                "meal_qr_terminals",
            ),
        ):
            try:
                conn.execute(text(ddl))
                print(f"Ensured '{label}' table.")
            except Exception as e:
                print(f"Note: {label}: {e}")

        try:
            conn.execute(text("ALTER TABLE meal_logs ADD COLUMN qr_terminal_id INT NULL"))
            print("Ensured 'qr_terminal_id' column in meal_logs")
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN code VARCHAR(50)"))
            print("Ensured 'code' column in companies")
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE employees ADD COLUMN department_id INTEGER"))
            print("Ensured 'department_id' column in employees")
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE employees ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
            print("Ensured 'is_verified' column in employees")
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255)"))
            print("Ensured 'password_hash' column in employees")
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE employees ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
            print("Ensured 'is_admin' column in employees")
        except Exception:
            pass

        try:
            result = conn.execute(text("DESCRIBE meal_logs"))
            columns = [row[0] for row in result.fetchall()]
            if "menu_id" in columns and "policy_id" not in columns:
                conn.execute(text("ALTER TABLE meal_logs CHANGE COLUMN menu_id policy_id INT(11)"))
                print("Migrated 'menu_id' to 'policy_id' in meal_logs")
            elif "policy_id" not in columns:
                conn.execute(text("ALTER TABLE meal_logs ADD COLUMN policy_id INT(11)"))
                print("Added 'policy_id' column to meal_logs")
        except Exception as e:
            print(f"Error ensuring 'policy_id' in meal_logs: {e}")

        print("\nOptimizing Foreign Key constraints (ON DELETE CASCADE)...")
        fk_configs = [
            ("departments", "company_id", "companies", "CASCADE"),
            ("employees", "company_id", "companies", "CASCADE"),
            ("employees", "department_id", "departments", "CASCADE"),
            ("meal_policies", "company_id", "companies", "CASCADE"),
            ("meal_logs", "user_id", "employees", "CASCADE"),
            ("meal_logs", "policy_id", "meal_policies", "CASCADE"),
            ("meal_logs", "void_operator_id", "employees", "SET NULL"),
            ("meal_logs", "qr_terminal_id", "meal_qr_terminals", "SET NULL"),
            ("audit_logs", "operator_id", "employees", "SET NULL"),
        ]

        for table, col, ref_table, on_delete in fk_configs:
            try:
                fk_query = text(
                    """
                    SELECT CONSTRAINT_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table
                    AND COLUMN_NAME = :col AND REFERENCED_TABLE_NAME IS NOT NULL
                """
                )
                res = conn.execute(
                    fk_query, {"db": db_name, "table": table, "col": col}
                )
                fk_name = res.scalar()

                if fk_name:
                    conn.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {fk_name}"))
                    print(f"  Dropped old FK {fk_name} on {table}({col})")

                new_fk_name = f"fk_{table}_{col}_{ref_table}"
                conn.execute(
                    text(
                        f"""
                    ALTER TABLE {table}
                    ADD CONSTRAINT {new_fk_name}
                    FOREIGN KEY ({col}) REFERENCES {ref_table}(id)
                    ON DELETE {on_delete}
                """
                    )
                )
                print(f"  Added Optimized FK {new_fk_name} (ON DELETE {on_delete})")
            except Exception as e:
                print(f"  Note: Skipped FK optimization for {table}({col}): {e}")

    Session = sessionmaker(bind=sync_engine, expire_on_commit=False)
    db = Session()
    try:
        res = db.execute(select(User).where(User.emp_no == "admin"))
        if res.scalar_one_or_none() is None:
            db.add(
                User(
                    id=1,
                    name="System Admin",
                    emp_no="admin",
                    status="ACTIVE",
                    social_provider="MANUAL",
                )
            )
            db.commit()
            print("Created default admin user (admin)")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error checking/creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

    sync_engine.dispose()


if __name__ == "__main__":
    repair()
