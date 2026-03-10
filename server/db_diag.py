
import os
import sys

# Add the app directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from sqlalchemy import create_engine, text
from app.config import settings

def diag():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("--- Diagnostic: User Table ---")
        try:
            result = conn.execute(text("SELECT id, username, employee_id, role, view_scope, is_headmaster FROM users WHERE username IN ('xz001', 'xz002') OR employee_id IN ('xz001', 'xz002')"))
            rows = result.fetchall()
            if not rows:
                print("No xz001 or xz002 found in users table.")
                # Look for similar names
                print("\nSearching for similar names...")
                res2 = conn.execute(text("SELECT id, username, employee_id FROM users LIMIT 20"))
                for r in res2:
                    print(f"ID: {r.id}, User: {r.username}, EmpID: {r.employee_id}")
            else:
                for row in rows:
                    print(f"ID: {row.id}, User: {row.username}, EmpID: {row.employee_id}, Role: {row.role}, Scope: {row.view_scope}, IsHM: {row.is_headmaster}")
            
            print("\n--- Statistics Table Summary ---")
            res3 = conn.execute(text("SELECT COUNT(*) as total FROM users WHERE role IN ('teacher', 'head_teacher') AND is_active = 1"))
            print(f"Total active teachers/headteachers: {res3.fetchone().total}")
            
            res4 = conn.execute(text("SELECT COUNT(*) as total FROM users WHERE is_headmaster = 1 AND is_active = 1"))
            print(f"Total active headmasters: {res4.fetchone().total}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    diag()
