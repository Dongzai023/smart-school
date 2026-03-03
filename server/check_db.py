
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Teacher

def check_data():
    db: Session = SessionLocal()
    count = db.query(Teacher).count()
    teachers = db.query(Teacher).limit(5).all()
    
    print(f"Total Teachers: {count}")
    print("--- Sample Data ---")
    for t in teachers:
        print(f"ID: {t.employee_id}, Name: {t.name}, Nickname: {t.nickname}, Group: {t.department_group}, Headmaster: {t.is_headmaster}")
    db.close()

if __name__ == "__main__":
    check_data()
