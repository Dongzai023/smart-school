from sqlalchemy import create_engine, text
from datetime import time
import os

# Use the same DATABASE_URL as in the app or a host-accessible one
# Since I'm running on the host, I should use localhost:3307 if the app is in docker
# Or just use the environment variable if defined.

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root123456@localhost:3307/signature_db?charset=utf8mb4"
)

def update_slots():
    engine = create_engine(DATABASE_URL)
    new_slots = [
        ("早晨教学时", "07:30:00", "08:10:00"),
        ("上午教学时", "10:40:00", "12:00:00"),
        ("下午教学时", "13:30:00", "14:20:00"),
        ("傍晚教学时", "16:30:00", "17:30:00"),
    ]
    
    print(f"Connecting to {DATABASE_URL}...")
    try:
        with engine.begin() as conn:
            for label, start, end in new_slots:
                # Update existing slots by label
                query = text("UPDATE time_slots SET start_time = :start, end_time = :end WHERE label = :label")
                result = conn.execute(query, {"start": start, "end": end, "label": label})
                print(f"Updated {label}: {result.rowcount} rows affected")
        print("✅ Database time slots updated successfully!")
    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    update_slots()
