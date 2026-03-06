
from sqlalchemy import create_engine, text
from app.config import settings

def hotfix_add_column():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for wx_openid column...")
        try:
            # Check if column exists
            result = conn.execute(text("SHOW COLUMNS FROM users LIKE 'wx_openid'"))
            if not result.fetchone():
                print("Column 'wx_openid' not found. Adding it...")
                conn.execute(text("ALTER TABLE users ADD COLUMN wx_openid VARCHAR(128) UNIQUE AFTER is_active"))
                conn.commit()
                print("Column 'wx_openid' added successfully.")
            else:
                print("Column 'wx_openid' already exists.")
        except Exception as e:
            print(f"Error updating database: {e}")

if __name__ == "__main__":
    hotfix_add_column()
