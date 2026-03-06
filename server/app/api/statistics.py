"""统计API"""

from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.checkin_record import CheckinRecord
from app.services.auth_service import get_current_user, require_admin, hash_password
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/statistics", tags=["统计"])


def _get_date_range(period: str):
    """根据周期返回起止日期"""
    today = date.today()
    if period == "week":
        # 本周一到今天
        start = today - timedelta(days=today.weekday())
    elif period == "month":
        start = today.replace(day=1)
    elif period == "semester":
        # 简化：近 180 天
        start = today - timedelta(days=180)
    else:
        start = today - timedelta(days=7)
    return start, today


def get_user_time_slots(is_headmaster: bool = False):
    """获取用户对应的时间段配置"""
    if is_headmaster:
        return [
            {"id": 1, "label": "早自习", "start": "06:20", "normal_end": "07:30", "late_end": "09:20"},
            {"id": 2, "label": "下午", "start": "13:30", "normal_end": "14:10", "late_end": "15:10"},
            {"id": 3, "label": "傍晚", "start": "16:30", "normal_end": "17:40", "late_end": "18:00"},
            {"id": 4, "label": "晚自习", "start": "18:00", "normal_end": "19:20", "late_end": "19:20"},
        ]
    else:
        return [
            {"id": 1, "label": "上午", "start": "07:30", "normal_end": "08:10", "late_end": "10:10"},
            {"id": 2, "label": "中午", "start": "10:40", "normal_end": "12:00", "late_end": "12:00"},
            {"id": 3, "label": "下午", "start": "13:30", "normal_end": "14:10", "late_end": "16:00"},
            {"id": 4, "label": "晚自习", "start": "16:30", "normal_end": "17:30", "late_end": "17:30"},
        ]


@router.get("/overview")
def get_overview(
    period: str = Query("week", description="周期: week/month/semester"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取统计概览"""
    start_date, end_date = _get_date_range(period)
    
    # 查询该时段内所有签到记录
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id,
        CheckinRecord.checkin_date >= start_date,
        CheckinRecord.checkin_date <= end_date
    ).all()
    
    signed_count = sum(1 for r in records if r.status in ("signed", "normal"))
    late_count = sum(1 for r in records if r.status == "late")
    absent_count = sum(1 for r in records if r.status == "absent")
    total = len(records)
    
    # 出勤率：(正常+迟到) / 总记录
    # 如果没有记录，基于工作日 * 时段数估算总应签次数
    if total > 0:
        attendance_rate = round(signed_count / total * 100, 1)
    else:
        # 估算：工作日天数 * 4 个时段
        work_days = sum(1 for i in range((end_date - start_date).days + 1)
                       if (start_date + timedelta(days=i)).weekday() < 5)
        is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
        slot_count = len(get_user_time_slots(is_headmaster))
        estimated_total = work_days * slot_count
        attendance_rate = round(signed_count / estimated_total * 100, 1) if estimated_total > 0 else 0
    
    # 全校排名
    rank_query = db.query(
        CheckinRecord.user_id,
        func.count(CheckinRecord.id).label("cnt")
    ).filter(
        CheckinRecord.status.in_(["signed", "normal", "late"]),
        CheckinRecord.checkin_date >= start_date,
        CheckinRecord.checkin_date <= end_date
    ).group_by(
        CheckinRecord.user_id
    ).order_by(
        func.count(CheckinRecord.id).desc()
    ).all()
    
    school_rank = 1
    for idx, r in enumerate(rank_query):
        if r.user_id == current_user.id:
            school_rank = idx + 1
            break
    
    # 排名评价
    if school_rank <= 10:
        rank_label = "卓越"
    elif school_rank <= 30:
        rank_label = "优秀"
    elif school_rank <= 60:
        rank_label = "良好"
    else:
        rank_label = "一般"
    
    return {
        "attendance_rate": attendance_rate,
        "signed_count": signed_count,
        "late_count": late_count,
        "absent_count": absent_count,
        "school_rank": school_rank,
        "rank_label": rank_label
    }


@router.get("/trend")
def get_trend(
    period: str = Query("week", description="周期: week/month/semester"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取签到趋势"""
    today = date.today()
    # 本周一
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    slot_count = len(get_user_time_slots(is_headmaster))
    day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    result = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        day_label = day_labels[i]
        
        # 查询当天签到数
        count = db.query(func.count(CheckinRecord.id)).filter(
            CheckinRecord.user_id == current_user.id,
            CheckinRecord.checkin_date == day_date,
            CheckinRecord.status.in_(["signed", "normal", "late"])
        ).scalar() or 0
        
        # 判断状态
        if day_date > today:
            status = "none"
        elif count >= slot_count:
            status = "full"
        elif count > 0:
            status = "partial"
        else:
            status = "absent"
        
        result.append({
            "day_label": day_label,
            "date": day_date.strftime("%Y-%m-%d"),
            "status": status,
            "signed_count": count,
            "total_slots": slot_count
        })
    
    return {"days": result}


@router.get("/timeslot")
def get_timeslot_stats(
    period: str = Query("week", description="周期: week/month/semester"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取时段分析"""
    start_date, end_date = _get_date_range(period)
    
    # 工作日天数
    work_days = sum(1 for i in range((end_date - start_date).days + 1)
                   if (start_date + timedelta(days=i)).weekday() < 5)
    
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    slots = get_user_time_slots(is_headmaster)
    
    result = []
    for slot in slots:
        signed = db.query(func.count(CheckinRecord.id)).filter(
            CheckinRecord.user_id == current_user.id,
            CheckinRecord.time_slot_id == slot["id"],
            CheckinRecord.checkin_date >= start_date,
            CheckinRecord.checkin_date <= end_date,
            CheckinRecord.status.in_(["signed", "normal"])
        ).scalar() or 0
        
        late = db.query(func.count(CheckinRecord.id)).filter(
            CheckinRecord.user_id == current_user.id,
            CheckinRecord.time_slot_id == slot["id"],
            CheckinRecord.checkin_date >= start_date,
            CheckinRecord.checkin_date <= end_date,
            CheckinRecord.status == "late"
        ).scalar() or 0
        
        total = work_days  # 每个时段每个工作日应签一次
        rate = round(signed / total * 100, 1) if total > 0 else 0
        
        result.append({
            "time_slot": {
                "id": slot["id"],
                "label": slot["label"],
                "start_time": slot["start"],
                "end_time": slot["normal_end"]
            },
            "signed_count": signed,
            "late_count": late,
            "total_count": total,
            "rate": rate
        })
    
    return {"items": result}


@router.get("/records")
def get_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取最近签到记录，按日期分组"""
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    slot_count = len(get_user_time_slots(is_headmaster))
    
    # 查询有签到记录的日期
    dates_query = db.query(
        func.distinct(CheckinRecord.checkin_date)
    ).filter(
        CheckinRecord.user_id == current_user.id
    ).order_by(
        CheckinRecord.checkin_date.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    total = db.query(
        func.count(func.distinct(CheckinRecord.checkin_date))
    ).filter(
        CheckinRecord.user_id == current_user.id
    ).scalar() or 0
    
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    
    records = []
    for (d,) in dates_query:
        day_records = db.query(CheckinRecord).filter(
            CheckinRecord.user_id == current_user.id,
            CheckinRecord.checkin_date == d
        ).all()
        
        # 该日整体状态
        has_late = any(r.status == "late" for r in day_records)
        has_absent = any(r.status == "absent" for r in day_records)
        slot_signed = {r.time_slot_id for r in day_records if r.status in ("signed", "normal", "late")}
        
        if has_absent or len(slot_signed) == 0:
            day_status = "absent"
        elif has_late:
            day_status = "late"
        else:
            day_status = "normal"
        
        # 最早签到时间
        first_time = None
        signed_records = [r for r in day_records if r.status in ("signed", "normal", "late")]
        if signed_records:
            earliest = min(signed_records, key=lambda r: r.checkin_time)
            first_time = earliest.checkin_time.strftime("%H:%M")
        
        records.append({
            "date": f"{d.year}年{d.month}月{d.day}日 {weekday_names[d.weekday()]}",
            "day": d.day,
            "month": month_names[d.month - 1],
            "weekday": weekday_names[d.weekday()],
            "status": day_status,
            "first_checkin_time": first_time,
            "location": day_records[0].location if day_records else "清涧中学"
        })
    
    return {"records": records, "total": total}


# ========================
# 管理员API
# ========================

@router.get("/admin/overview")
def admin_get_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员获取全校签到概览"""
    today = date.today()
    
    # 今日应签到人数
    total_users = db.query(User).filter(User.is_active == True).count()
    
    # 今日已签到人数
    today_start = datetime.combine(today, datetime.min.time())
    signed_today = db.query(func.count(func.distinct(CheckinRecord.user_id))).filter(
        CheckinRecord.checkin_date == today,
        CheckinRecord.status.in_(["signed", "normal", "late"])
    ).scalar() or 0
    
    # 今日迟到人数
    late_today = db.query(func.count(func.distinct(CheckinRecord.user_id))).filter(
        CheckinRecord.checkin_date == today,
        CheckinRecord.status == "late"
    ).scalar() or 0
    
    # 今日未签人数
    absent_today = total_users - signed_today
    
    return {
        "total_users": total_users,
        "signed_today": signed_today,
        "late_today": late_today,
        "absent_today": absent_today,
        "attendance_rate": round(signed_today / total_users * 100, 1) if total_users > 0 else 0
    }


@router.get("/admin/users")
def admin_get_user_stats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department: str = Query(None, description="部门筛选"),
    period: str = Query("week", description="统计周期"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    role: str = Query(None, description="角色筛选")
):
    """管理员获取所有用户的签到统计"""
    start_date, end_date = _get_date_range(period)
    
    # 获取所有用户
    query = db.query(User).filter(User.is_active == True)
    if department:
        query = query.filter(User.department == department)
    if role:
        query = query.filter(User.role == role)
    
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 获取部门列表
    departments = db.query(func.distinct(User.department)).filter(
        User.department != None,
        User.department != ""
    ).all()
    department_list = [d[0] for d in departments]
    
    result = []
    for user in users:
        # 统计该用户在不同时段的签到情况
        records = db.query(CheckinRecord).filter(
            CheckinRecord.user_id == user.id,
            CheckinRecord.checkin_date >= start_date,
            CheckinRecord.checkin_date <= end_date
        ).all()
        
        signed = sum(1 for r in records if r.status in ("signed", "normal"))
        late = sum(1 for r in records if r.status == "late")
        absent = sum(1 for r in records if r.status == "absent")
        
        # 计算应签到次数（工作日 * 时段数）
        work_days = sum(1 for i in range((end_date - start_date).days + 1)
                       if (start_date + timedelta(days=i)).weekday() < 5)
        is_headmaster = user.is_headmaster or user.role == "head_teacher"
        slot_count = len(get_user_time_slots(is_headmaster))
        expected = work_days * slot_count
        
        result.append({
            "id": user.id,
            "username": user.username,
            "employee_id": user.employee_id or user.username,
            "real_name": user.real_name,
            "department": user.department or "",
            "role": user.role,
            "is_headmaster": user.is_headmaster or user.role == "head_teacher",
            "is_verified": user.is_verified or False,
            "signed_count": signed,
            "late_count": late,
            "absent_count": absent,
            "expected_count": expected,
            "attendance_rate": round(signed / expected * 100, 1) if expected > 0 else 0
        })
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "departments": department_list
    }


@router.get("/admin/user/{user_id}/records")
def admin_get_user_records(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=50),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员获取指定用户的签到记录"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 查询签到记录
    records_query = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).order_by(CheckinRecord.checkin_date.desc(), CheckinRecord.time_slot_id)
    
    total = records_query.count()
    records = records_query.offset((page - 1) * page_size).limit(page_size).all()
    
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "date": r.checkin_date.strftime("%Y-%m-%d") if r.checkin_date else None,
            "weekday": weekday_names[r.checkin_date.weekday()] if r.checkin_date else "",
            "time_slot_id": r.time_slot_id,
            "time": r.checkin_time.strftime("%H:%M") if r.checkin_time else "",
            "status": r.status,
            "location": r.location or ""
        })
    
    return {
        "user": {
            "id": user.id,
            "real_name": user.real_name,
            "employee_id": user.employee_id or user.username,
            "department": user.department or ""
        },
        "records": result,
        "total": total
    }

@router.get("/principal/checkin")
def get_principal_checkin(
    checkin_date: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """校长端查看全校/班主任签到情况"""
    if current_user.role != "principal" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问")

    if not checkin_date:
        checkin_date = date.today()

    # 根据权限范围确定要查看的用户列表
    user_query = db.query(User).filter(User.is_active == True)
    if current_user.view_scope == "head_teacher":
        user_query = user_query.filter(User.is_headmaster == True)
    
    # 排除管理员和校长自身（除非需要）
    teachers = user_query.filter(User.role == "teacher").all()
    teacher_ids = [t.id for t in teachers]

    # 获取当天的所有签到记录
    records = db.query(CheckinRecord).filter(
        CheckinRecord.checkin_date == checkin_date,
        CheckinRecord.user_id.in_(teacher_ids)
    ).all()

    # 聚合数据
    record_map = {} # user_id -> [records]
    for r in records:
        if r.user_id not in record_map:
            record_map[r.user_id] = []
        record_map[r.user_id].append(r)

    results = []
    summary = {
        "total": len(teachers),
        "signed": 0,
        "late": 0,
        "absent": 0
    }

    for t in teachers:
        t_records = record_map.get(t.id, [])
        # 简单逻辑：如果今天有任何一条签到记录
        has_signed = any(r.status in ("signed", "normal") for r in t_records)
        has_late = any(r.status == "late" for r in t_records)
        
        status = "absent"
        if has_signed:
            status = "signed"
            summary["signed"] += 1
        elif has_late:
            status = "late"
            summary["late"] += 1
        else:
            summary["absent"] += 1

        results.append({
            "id": t.id,
            "real_name": t.real_name,
            "nickname": t.nickname,
            "department": t.department,
            "is_headmaster": t.is_headmaster,
            "status": status,
            "details": [
                {
                    "label": r.time_slot_label,
                    "time": r.checkin_time.strftime("%H:%M") if r.checkin_time else None,
                    "status": r.status
                } for r in t_records
            ]
        })

    return {
        "date": checkin_date.isoformat(),
        "summary": summary,
        "teachers": results
    }
