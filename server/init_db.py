"""数据库初始化脚本 - 建表 + 插入种子数据"""
import os
import sys
from datetime import datetime, date, time, timedelta

# 确保能导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models import Teacher, TimeSlot, CheckinRecord, Achievement, TeacherAchievement
from app.auth import get_password_hash


def init_database():
    """初始化数据库"""
    print("🔧 开始初始化数据库...")

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 数据表创建完成")

    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing_teacher = db.query(Teacher).first()
        if existing_teacher:
            print("ℹ️  数据库已有数据，跳过种子数据插入")
            return

        # ========== 1. 创建教师 ==========
        teacher1 = Teacher(
            employee_id="QJ202309001",
            name="张晓东",
            password_hash=get_password_hash("123456"),
            department="技术组",
            nickname="树苗哥哥",
            email="zhangxiaodong@qingjian.edu.cn",
            is_verified=True
        )
        teacher2 = Teacher(
            employee_id="QJ202309002",
            name="李明",
            password_hash=get_password_hash("123456"),
            department="教学组",
            nickname="小明老师",
            email="liming@qingjian.edu.cn",
            is_verified=True
        )
        teacher3 = Teacher(
            employee_id="QJ202309003",
            name="王芳",
            password_hash=get_password_hash("123456"),
            department="行政组",
            nickname="芳姐",
            email="wangfang@qingjian.edu.cn",
            is_verified=True
        )
        db.add_all([teacher1, teacher2, teacher3])
        db.flush()
        print(f"✅ 创建了 3 位教师（张晓东 ID={teacher1.id}）")

        # ========== 2. 创建签到时段 ==========
        slots = [
            TimeSlot(start_time=time(7, 30), end_time=time(8, 10), label="早晨教学时", sort_order=1),
            TimeSlot(start_time=time(10, 40), end_time=time(12, 0), label="上午教学时", sort_order=2),
            TimeSlot(start_time=time(13, 30), end_time=time(14, 20), label="下午教学时", sort_order=3),
            TimeSlot(start_time=time(16, 30), end_time=time(17, 30), label="傍晚教学时", sort_order=4),
        ]
        db.add_all(slots)
        db.flush()
        print(f"✅ 创建了 4 个签到时段")

        # ========== 3. 创建历史签到记录 ==========
        today = date.today()
        records = []

        # 生成过去 14 天的签到记录（工作日）
        for day_offset in range(14, 0, -1):
            d = today - timedelta(days=day_offset)
            if d.weekday() >= 5:  # 跳过周末
                continue

            for teacher in [teacher1, teacher2, teacher3]:
                for slot in slots:
                    # 模拟不同状态
                    import random
                    random.seed(hash((teacher.id, slot.id, d.toordinal())))
                    rand_val = random.random()

                    if rand_val < 0.80:
                        status = "normal"
                        # 正常签到：在时段开始时间后 5-30 分钟
                        minutes_after = random.randint(5, 30)
                        checkin_dt = datetime.combine(d, slot.start_time) + timedelta(minutes=minutes_after)
                    elif rand_val < 0.92:
                        status = "late"
                        # 迟到：在时段结束时间后 5-25 分钟
                        minutes_after = random.randint(5, 25)
                        checkin_dt = datetime.combine(d, slot.end_time) + timedelta(minutes=minutes_after)
                    else:
                        status = "absent"
                        checkin_dt = datetime.combine(d, slot.start_time)

                    records.append(CheckinRecord(
                        teacher_id=teacher.id,
                        time_slot_id=slot.id,
                        checkin_date=d,
                        checkin_time=checkin_dt,
                        status=status,
                        location="清涧中学教学楼"
                    ))

        db.add_all(records)
        db.flush()
        print(f"✅ 创建了 {len(records)} 条历史签到记录")

        # ========== 4. 创建成就勋章 ==========
        achievements = [
            Achievement(name="全勤王", emoji="🏆", description="连续30天全勤",
                       condition_key="consecutive_full", condition_value=30),
            Achievement(name="早起鸟", emoji="⚡", description="连续7天早签",
                       condition_key="consecutive_early", condition_value=7),
            Achievement(name="准时达人", emoji="🎯", description="从不迟到",
                       condition_key="never_late", condition_value=0),
            Achievement(name="进步之星", emoji="📈", description="连续提升",
                       condition_key="improvement", condition_value=3),
            Achievement(name="完美主义", emoji="💎", description="月度满分",
                       condition_key="monthly_perfect", condition_value=1),
            Achievement(name="新人上路", emoji="🌟", description="完成首次签到",
                       condition_key="first_checkin", condition_value=1),
        ]
        db.add_all(achievements)
        db.flush()
        print(f"✅ 创建了 {len(achievements)} 个成就勋章")

        # ========== 5. 给张晓东解锁部分成就 ==========
        # 解锁: 全勤王、早起鸟、进步之星、新人上路（4/6）
        unlocked_indices = [0, 1, 3, 5]  # 全勤王、早起鸟、进步之星、新人上路
        for idx in unlocked_indices:
            ta = TeacherAchievement(
                teacher_id=teacher1.id,
                achievement_id=achievements[idx].id,
                unlocked_at=datetime.now() - timedelta(days=idx * 3)
            )
            db.add(ta)

        db.commit()
        print("✅ 种子数据插入完成")
        print(f"\n🎉 数据库初始化完成！")
        print(f"📋 测试账号: 工号 QJ202309001 / 密码 123456")
        print(f"📋 备用账号: 工号 QJ202309002 / 密码 123456")
        print(f"📋 备用账号: 工号 QJ202309003 / 密码 123456")

    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
