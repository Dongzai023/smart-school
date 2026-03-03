import os
import sys
from app.database import SessionLocal
from app.models import Teacher
from app.auth import get_password_hash

def add_teacher(employee_id, name, password, department="测试组", nickname="测试用户"):
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing = db.query(Teacher).filter(Teacher.employee_id == employee_id).first()
        if existing:
            print(f"用户 {employee_id} 已存在。")
            return

        new_teacher = Teacher(
            employee_id=employee_id,
            name=name,
            password_hash=get_password_hash(password),
            department=department,
            nickname=nickname,
            is_verified=True
        )
        db.add(new_teacher)
        db.commit()
        print(f"成功添加用户: {name} ({employee_id})")
    except Exception as e:
        db.rollback()
        print(f"添加用户失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python add_user.py <工号> <姓名> <密码>")
        sys.exit(1)
    
    employee_id = sys.argv[1]
    name = sys.argv[2]
    password = sys.argv[3]
    add_teacher(employee_id, name, password)
