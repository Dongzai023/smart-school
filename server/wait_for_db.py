"""等待 MySQL 数据库就绪"""
import time
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root123456@mysql:3306/signature_db?charset=utf8mb4"
)

def wait_for_db(max_retries=30, delay=2):
    """等待数据库连接就绪"""
    engine = create_engine(DATABASE_URL)
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ 数据库连接成功！")
            engine.dispose()
            return
        except Exception as e:
            print(f"⏳ 等待数据库就绪... ({i+1}/{max_retries}) - {e}")
            time.sleep(delay)
    
    engine.dispose()
    raise Exception("❌ 数据库连接超时，请检查 MySQL 服务是否正常运行")

if __name__ == "__main__":
    wait_for_db()
