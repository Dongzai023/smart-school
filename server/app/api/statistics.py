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
from app.config import settings
from app.api.checkin import get_user_time_slots
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
    current_user: User = Depends(get_current_user)
):
    """管理员/校长获取全校签到概览"""
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(status_code=403, detail="需要管理权限")
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
    current_user: User = Depends(get_current_user),
    role: str = Query(None, description="角色筛选")
):
    """管理员/校长获取所有用户的签到统计"""
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(status_code=403, detail="需要管理权限")
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
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
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
    current_user: User = Depends(get_current_user)
):
    """管理员/校长获取指定用户的签到记录"""
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(status_code=403, detail="需要管理权限")
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

@router.get("/diag/users")
def diag_users(db: Session = Depends(get_db)):
    """Diagnostic endpoint to check test users."""
    users = db.query(User).filter(User.username.like("%xz%")).all()
    return [{"id": u.id, "username": u.username, "role": u.role, "scope": u.view_scope, "is_hm": u.is_headmaster, "emp_id": u.employee_id} for u in users]

@router.get("/principal/dashboard")
def principal_get_dashboard(
    period: str = Query("today", description="周期: session/today/week/month/semester"),
    checkin_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """校长端多维度签到看板"""
    # DEBUG LOGGING (Move to top to capture 403 cases)
    try:
        import os
        # Ensure folder exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        log_path = os.path.join(settings.UPLOAD_DIR, "debug_user.log")
        with open(log_path, "a") as f:
            from datetime import datetime
            f.write(f"{datetime.now()} - Dashboard Access - User: {current_user.username}, Role: {current_user.role}, Scope: {current_user.view_scope}, EmpID: {current_user.employee_id}\n")
    except:
        pass

    # 允许特定测试账号访问
    whitelisted = ["xz001", "xz002", "T15229628942"]
    curr_name = str(current_user.username).strip().lower()
    curr_emp_id = str(current_user.employee_id).strip().lower() if getattr(current_user, 'employee_id', None) else ""
    
    is_test = (curr_name in whitelisted) or (curr_emp_id in whitelisted)
    is_authorized = (current_user.role in ["admin", "principal"]) or is_test
    
    if not is_authorized:
        # 更加宽松：如果是教育处等管理视角，也允许
        if current_user.view_scope == "all" or current_user.role == "head_teacher":
            is_authorized = True
        else:
            raise HTTPException(status_code=403, detail=f"无权访问 (Debug: {curr_name}/{current_user.role})")

    if not checkin_date:
        checkin_date = date.today()

    # 1. 确定时间范围与时段
    start_date = checkin_date
    end_date = checkin_date
    is_session_mode = (period == "session")
    
    if period == "week":
        start_date = checkin_date - timedelta(days=checkin_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "month":
        start_date = checkin_date.replace(day=1)
        # 简单处理：本月最后一天
        if start_date.month == 12:
            end_date = date(start_date.year, 12, 31)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
    elif period == "semester":
        # 近 180 天
        start_date = checkin_date - timedelta(days=180)
        end_date = checkin_date

    # 1. 确定标题与权限范围
    username = str(current_user.username).strip().lower()
    employee_id = str(current_user.employee_id).strip().lower() if getattr(current_user, 'employee_id', None) else ""
    
    # 彻底检查 xz001 和 xz002 标识
    is_xz001 = (username == "xz001" or employee_id == "xz001")
    is_xz002 = (username == "xz002" or employee_id == "xz002")
    
    dashboard_title = "清涧中学签到数据看板"
    force_headmaster_view = False
    
    # xz001 优先级最高：看全校
    if is_xz001:
        dashboard_title = "清涧中学签到数据看板"
        force_headmaster_view = False
    # xz002 优先级 second：仅看班主任
    elif is_xz002:
        dashboard_title = "清涧中学班主任签到数据看板"
        force_headmaster_view = True
    # 其他根据权限范围判定
    elif current_user.view_scope == "head_teacher" or current_user.role == "head_teacher":
        dashboard_title = "清涧中学班主任签到数据看板"
        force_headmaster_view = True
    else:
        dashboard_title = "清涧中学签到数据看板"
        force_headmaster_view = False

    # 2. 确定用户范围
    user_query = db.query(User).filter(User.is_active == True)
    
    if force_headmaster_view:
        user_query = user_query.filter(User.is_headmaster == True)
    
    # 核心：获取所有展示对象 (排除管理员和当前查看者)
    teachers = user_query.filter(User.role != "admin", User.id != current_user.id).all()
    teacher_ids = [t.id for t in teachers]

    # 3. 获取签到记录
    if not teacher_ids:
        # 如果没有符合条件的老师，返回空统计
        summary = {"total": 0, "normal_count": 0, "late_count": 0, "absent_count": 0, "rate": 0, "leave_count": 0}
        return {
            "period": period,
            "dashboard_title": dashboard_title,
            "session_label": None,
            "date_range": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
            "summary": summary,
            "categories": {"normal": [], "late": [], "absent": []},
            "debug_user": {
                "id": current_user.id,
                "username": username,
                "emp_id": employee_id,
                "is_xz001": is_xz001,
                "is_xz002": is_xz002,
                "force_hm": force_headmaster_view,
                "msg": "No teachers found matching criteria"
            }
        }

    records_query = db.query(CheckinRecord).filter(
        CheckinRecord.user_id.in_(teacher_ids),
        CheckinRecord.checkin_date >= start_date,
        CheckinRecord.checkin_date <= end_date
    )
    
    # 特殊处理：本次 (Session) 模式
    current_slot = None
    if is_session_mode:
        from datetime import time as dt_time
        now_time_obj = datetime.now().time()
        # 统一使用教师时段作为默认校级展示参考
        slots = get_user_time_slots(False)
        for s in reversed(slots):
            # s["start"] 是 datetime.time 对象
            if now_time_obj >= s["start"]:
                current_slot = s
                break
        if not current_slot: current_slot = slots[0]
        
        records_query = records_query.filter(
            CheckinRecord.checkin_date == checkin_date,
            CheckinRecord.time_slot_id == current_slot["id"]
        )

    records = records_query.all()

    # 4. 数据聚合与人员分类
    record_map = {}
    for r in records:
        if r.user_id not in record_map: record_map[r.user_id] = []
        record_map[r.user_id].append(r)

    categories = {
        "normal": [], # 正常
        "late": [],   # 迟到
        "absent": []  # 未签
    }

    for t in teachers:
        t_records = record_map.get(t.id, [])
        teacher_info = {
            "id": t.id,
            "real_name": t.real_name,
            "nickname": t.nickname,
            "avatar_url": t.avatar_url,
            "department": t.department or "校办公室",
            "is_headmaster": t.is_headmaster,
            "record_count": len(t_records)
        }

        if is_session_mode or period == "today":
            has_signed = any(r.status in ("signed", "normal") for r in t_records)
            has_late = any(r.status == "late" for r in t_records)
            if has_signed: categories["normal"].append(teacher_info)
            elif has_late: categories["late"].append(teacher_info)
            else: categories["absent"].append(teacher_info)
        else:
            has_absent = any(r.status == "absent" for r in t_records)
            has_late = any(r.status == "late" for r in t_records)
            
            if not t_records:
                categories["absent"].append(teacher_info)
            elif has_absent:
                categories["absent"].append(teacher_info)
            elif has_late:
                categories["late"].append(teacher_info)
            else:
                categories["normal"].append(teacher_info)

    total_teachers = len(teachers)
    summary = {
        "total": total_teachers,
        "normal_count": len(categories["normal"]),
        "late_count": len(categories["late"]),
        "absent_count": len(categories["absent"]),
        "leave_count": 0, # Placeholder
        "rate": round(len(categories["normal"]) / total_teachers * 100, 1) if total_teachers else 0
    }

    return {
        "period": period,
        "dashboard_title": dashboard_title,
        "session_label": current_slot["label"] if current_slot else None,
        "date_range": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
        "summary": summary,
        "categories": categories,
        "debug_user": {
            "id": current_user.id,
            "username": username,
            "employee_id": employee_id,
            "role": current_user.role,
            "view_scope": current_user.view_scope,
            "is_xz001": is_xz001,
            "is_xz002": is_xz002,
            "force_headmaster": force_headmaster_view,
            "teacher_count": len(teachers)
        }
    }
