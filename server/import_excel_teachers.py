
import openpyxl
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Teacher
from app.auth import get_password_hash
import os

def import_teachers(file_path: str):
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    try:
        # 加载 Excel 工作簿
        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active
        
        # 获取表头
        headers = [cell.value for cell in sheet[1]]
        
        # 列名映射
        mapping = {
            "教工号": None,
            "姓名": None,
            "昵称": None,
            "所属教研组": None,
            "是否班主任": None
        }
        
        for i, header in enumerate(headers):
            if header in mapping:
                mapping[header] = i
        
        # 检查必要列
        if mapping["教工号"] is None or mapping["姓名"] is None:
            print("错误: Excel 表格必须包含 '教工号' 和 '姓名' 列")
            return

        db: Session = SessionLocal()
        default_password_hash = get_password_hash("123456")
        
        success_count = 0
        skip_count = 0
        
        # 从第二行开始读取数据
        for row in sheet.iter_rows(min_row=2, values_only=True):
            emp_id = str(row[mapping["教工号"]]) if row[mapping["教工号"]] is not None else None
            if not emp_id:
                continue
                
            # 检查工号是否已存在
            existing = db.query(Teacher).filter(Teacher.employee_id == emp_id).first()
            if existing:
                print(f"跳过: 工号 {emp_id} 已存在")
                skip_count += 1
                continue
            
            name = str(row[mapping["姓名"]])
            nickname = str(row[mapping["昵称"]]) if mapping["昵称"] is not None and row[mapping["昵称"]] else ""
            dept_group = str(row[mapping["所属教研组"]]) if mapping["所属教研组"] is not None and row[mapping["所属教研组"]] else ""
            
            is_headmaster = False
            if mapping["是否班主任"] is not None and row[mapping["是否班主任"]]:
                val = str(row[mapping["是否班主任"]]).strip()
                is_headmaster = val in ['是', '1', 'True', 'true', 'Y', 'y']

            new_teacher = Teacher(
                employee_id=emp_id,
                name=name,
                nickname=nickname,
                department_group=dept_group,
                is_headmaster=is_headmaster,
                password_hash=default_password_hash,
                is_verified=True
            )
            db.add(new_teacher)
            success_count += 1
            
        db.commit()
        db.close()
        
        print(f"导入完成！成功: {success_count}, 跳过: {skip_count}")
        
    except Exception as e:
        print(f"导入出错: {str(e)}")

if __name__ == "__main__":
    import_teachers("teachers.xlsx")
