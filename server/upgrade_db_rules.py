"""Script to inject role-based time slots and update database schema"""
import os
import sys

# Ensure app module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import time
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import TimeSlot


def upgrade_db_rules():
    print("🔧 Upgrading database for role-based check-in rules...")
    
    with engine.connect() as conn:
        try:
            # 1. Add is_headmaster to teachers
            try:
                conn.execute(text("ALTER TABLE teachers ADD COLUMN is_headmaster BOOLEAN DEFAULT FALSE COMMENT '是否为班主任'"))
                conn.commit()
                print("✅ Added is_headmaster to teachers")
            except Exception as e:
                print(f"⚠️ Could not add is_headmaster (may already exist): {e}")

            # 2. Modify time_slots table schema
            try:
                # 尝试添加新列
                conn.execute(text("ALTER TABLE time_slots ADD COLUMN role_type VARCHAR(20) DEFAULT 'normal' COMMENT '适用角色: normal / headmaster'"))
                conn.execute(text("ALTER TABLE time_slots ADD COLUMN checkin_start TIME COMMENT '开始打卡时间'"))
                conn.execute(text("ALTER TABLE time_slots ADD COLUMN normal_end TIME COMMENT '正常打卡结束时间'"))
                conn.execute(text("ALTER TABLE time_slots ADD COLUMN late_end TIME COMMENT '迟到打卡结束时间'"))
                conn.commit()
                print("✅ Added new bounds to time_slots")
            except Exception as e:
                print(f"⚠️ Could not add new bounds to time_slots: {e}")

            # Note: SQLite / Some MySQL setups struggle with ALTER TABLE DROP COLUMN
            # But we must drop it because older versions had it as NOT NULL, which blocks inserting new rows.
            try:
                conn.execute(text("ALTER TABLE time_slots DROP COLUMN start_time"))
                conn.execute(text("ALTER TABLE time_slots DROP COLUMN end_time"))
                conn.commit()
                print("✅ Dropped old NOT NULL columns start_time and end_time")
            except Exception as e:
                print(f"⚠️ Could not drop old columns (may already be dropped): {e}")

            # 3. Clean up existing TimeSlots and CheckinRecords referencing old slots safely
            print("Cleaning up old checkin records to prevent TimeSlot foreign key errors...")
            conn.execute(text("DELETE FROM checkin_records"))
            conn.execute(text("DELETE FROM time_slots"))
            conn.commit()
                
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return

    # 4. Insert New Rules
    print("Seeding new role-based time slots...")
    db = SessionLocal()
    try:
        slots = [
            # 普通教师（科任教师）时段
            TimeSlot(role_type="normal", checkin_start=time(7, 30), normal_end=time(8, 10), late_end=time(10, 10), label="早晨签到", sort_order=1),
            TimeSlot(role_type="normal", checkin_start=time(10, 40), normal_end=time(12, 0), late_end=time(12, 0), label="中午签到", sort_order=2),
            TimeSlot(role_type="normal", checkin_start=time(13, 30), normal_end=time(14, 10), late_end=time(16, 0), label="下午签到", sort_order=3),
            TimeSlot(role_type="normal", checkin_start=time(16, 30), normal_end=time(17, 30), late_end=time(17, 30), label="傍晚签到", sort_order=4),
            
            # 班主任时段
            TimeSlot(role_type="headmaster", checkin_start=time(6, 20), normal_end=time(7, 30), late_end=time(9, 20), label="晨读签到", sort_order=1),
            TimeSlot(role_type="headmaster", checkin_start=time(13, 30), normal_end=time(14, 10), late_end=time(15, 10), label="下午签到", sort_order=2),
            TimeSlot(role_type="headmaster", checkin_start=time(16, 30), normal_end=time(17, 40), late_end=time(17, 40), label="傍晚签到", sort_order=3),
            TimeSlot(role_type="headmaster", checkin_start=time(18, 0), normal_end=time(19, 20), late_end=time(19, 20), label="晚修签到", sort_order=4),
        ]
        db.add_all(slots)
        db.commit()
        print(f"✅ Created {len(slots)} new rule slots successfully.")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding rules failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    upgrade_db_rules()
