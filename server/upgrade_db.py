"""Script to add new columns to teachers table"""
import os
import sys

# Ensure app module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

def upgrade_db():
    print("🔧 Upgrading database...")
    
    with engine.connect() as conn:
        try:
            # Add columns. Use IF NOT EXISTS to avoid errors if they already exist, but MySQL doesn't natively support IF NOT EXISTS for ADD COLUMN in older versions. 
            # We will catch exceptions for individual columns or just try executing all
            
            queries = [
                "ALTER TABLE teachers ADD COLUMN gender VARCHAR(10) DEFAULT '未知' COMMENT '性别'",
                "ALTER TABLE teachers ADD COLUMN phone VARCHAR(20) DEFAULT '' COMMENT '手机号'",
                "ALTER TABLE teachers ADD COLUMN teaching_subject VARCHAR(50) DEFAULT '' COMMENT '所教学科'",
                "ALTER TABLE teachers ADD COLUMN department_group VARCHAR(100) DEFAULT '' COMMENT '所属教研组'",
                "ALTER TABLE teachers ADD COLUMN grade VARCHAR(50) DEFAULT '' COMMENT '所属年级'",
                "ALTER TABLE teachers ADD COLUMN class_name VARCHAR(50) DEFAULT '' COMMENT '所属班级'",
            ]
            
            for query in queries:
                try:
                    conn.execute(text(query))
                    conn.commit()
                    print(f"✅ Executed: {query}")
                except Exception as e:
                    print(f"⚠️ Could not execute '{query}': {e}")
                    
            print("✅ Database upgrade completed")
        except Exception as e:
            print(f"❌ Database upgrade failed: {e}")

if __name__ == "__main__":
    upgrade_db()
