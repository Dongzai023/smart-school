
import os
import sys

# Add the app directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'app'))

try:
    from sqlalchemy import create_engine, text
    from app.config import settings
    
    print(f"Connecting to: {settings.DB_HOST}:{settings.DB_PORT}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("--- Checking User: T18329284080 ---")
        query = text("SELECT id, username, employee_id, real_name, role, is_active, wx_openid FROM users WHERE employee_id = 'T18329284080' OR username = 'T18329284080'")
        result = conn.execute(query)
        row = result.fetchone()
        
        if row:
            print(f"ID: {row.id}")
            print(f"Username: {row.username}")
            print(f"Employee ID: {row.employee_id}")
            print(f"Real Name: {row.real_name}")
            print(f"Role: {row.role}")
            print(f"Is Active: {row.is_active}")
            print(f"OpenID: {row.wx_openid}")
            
            if not row.is_active:
                print("\nALERT: User is NOT active. This is likely causing the 430/401 errors.")
            if not row.wx_openid:
                print("\nALERT: User has NO WeChat OpenID bound. Silent login (wx-login) will fail.")
        else:
            print("User T18329284080 not found in database.")
            
            # Check for similar IDs
            print("\nSearching for similar employee IDs...")
            res2 = conn.execute(text("SELECT employee_id, real_name FROM users WHERE employee_id LIKE '%18329284080%'"))
            similar = res2.fetchall()
            for s in similar:
                print(f"Found match: {s.employee_id} ({s.real_name})")

except Exception as e:
    print(f"Error: {e}")
