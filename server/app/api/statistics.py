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
import logging

logger = logging.getLogger(__name__)

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
    user_id: Optional[int] = Query(None, description="目标用户ID (管理员权限)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取统计概览"""
    target_user_id = current_user.id
    username = str(current_user.username).strip().lower()
    employee_id = str(current_user.employee_id).strip().lower() if getattr(current_user, 'employee_id', None) else ""
    whitelisted = ["xz001", "xz002", "t15229628942"]
    
    is_whitelisted = (username in whitelisted) or (employee_id in whitelisted)
    is_mgmt = (current_user.role in ["admin", "principal"]) or (current_user.view_scope in ["all", "head_teacher"])
    is_auth_for_all = is_whitelisted or is_mgmt
    
    if user_id and is_auth_for_all:
        target_user_id = user_id
    elif user_id and user_id != current_user.id:
        logger.warning(f"get_overview: User {username} (ID: {current_user.id}, scope: {current_user.view_scope}) denied access to user ID {user_id}. auth_for_all={is_auth_for_all}")
        
    logger.info(f"get_overview: current_user={username}, target_user_id={target_user_id}, period={period}")
        
    # 处理 session 周期，session 模式下我们看今天的数据
    if period == "session":
        start_date = date.today()
        end_date = date.today()
    else:
        start_date, end_date = _get_date_range(period)
    
    # 1. 获取目标用户的身份来确定打卡时段数
    target_user = current_user
    if target_user_id != current_user.id:
        target_user = db.query(User).filter(User.id == target_user_id).first() or current_user
    
    is_headmaster = target_user.is_headmaster or target_user.role == "head_teacher"
    slots = get_user_time_slots(is_headmaster)
    slot_count = len(slots)
    
    # 2. 查询该时段内所有签到记录
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == target_user_id,
        CheckinRecord.checkin_date >= start_date,
        CheckinRecord.checkin_date <= end_date
    ).all()
    
    signed_count = sum(1 for r in records if r.status in ("signed", "normal"))
    late_count = sum(1 for r in records if r.status == "late")
    
    # 3. 计算应签到次数并推算缺勤
    if period == "session":
        # 如果是 session 模式，应签到次数取决于当前已经过去的时段
        now_time = datetime.now().time()
        now_minutes = now_time.hour * 60 + now_time.minute
        expected_total = sum(1 for s in slots if (s["start"].hour * 60 + s["start"].minute) <= now_minutes)
    else:
        # 工作日天数 * 时段数
        work_days = sum(1 for i in range((end_date - start_date).days + 1)
                       if (start_date + timedelta(days=i)).weekday() < 5)
        expected_total = work_days * slot_count
        
    # 计算缺勤（核心修复：absent 不一定存在于 DB 中）
    absent_count = max(0, expected_total - signed_count - late_count)
    
    # 出勤率：(正常+迟到) / 总应签
    attendance_rate = 0
    if expected_total > 0:
        attendance_rate = round((signed_count + late_count) / expected_total * 100, 1)
    
    # 全校排名 (基于目标点位)
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
        if r.user_id == target_user_id:
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
        "attendance_rate": min(100.0, attendance_rate),
        "signed_count": signed_count,
        "late_count": late_count,
        "absent_count": absent_count,
        "total_count": expected_total,
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
    user_id: Optional[int] = Query(None, description="目标用户ID (管理员权限)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取最近签到记录，按日期分组"""
    target_user_id = current_user.id
    username = str(current_user.username).strip().lower()
    employee_id = str(current_user.employee_id).strip().lower() if getattr(current_user, 'employee_id', None) else ""
    whitelisted = ["xz001", "xz002", "t15229628942"]
    
    is_whitelisted = (username in whitelisted) or (employee_id in whitelisted)
    is_mgmt = (current_user.role in ["admin", "principal"]) or (current_user.view_scope in ["all", "head_teacher"])
    is_auth_for_all = is_whitelisted or is_mgmt
    
    if user_id and is_auth_for_all:
        target_user_id = user_id
    elif user_id and user_id != current_user.id:
        logger.warning(f"get_records: User {username} (ID: {current_user.id}) denied access to user ID {user_id}. auth_for_all={is_auth_for_all}")
    
    logger.info(f"get_records: current_user={username}, target_user_id={target_user_id}, page={page}")
    
    # 注意：slot_count 逻辑依赖于目标用户身份，但为简化，目前校长端和老师端差异主要在展示
    # 这里的 slot_count 实际用于前端逻辑，后端仅返回记录
    
    # 查询有签到记录的日期
    dates_query = db.query(
        func.distinct(CheckinRecord.checkin_date)
    ).filter(
        CheckinRecord.user_id == target_user_id
    ).order_by(
        CheckinRecord.checkin_date.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    total = db.query(
        func.count(func.distinct(CheckinRecord.checkin_date))
    ).filter(
        CheckinRecord.user_id == target_user_id
    ).scalar() or 0
    
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    
    records = []
    for (d,) in dates_query:
        day_records = db.query(CheckinRecord).filter(
            CheckinRecord.user_id == target_user_id,
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

@router.get("/principal/dashboard")
def principal_get_dashboard(
    period: str = Query("today", description="周期: session/today/week/month/semester"),
    checkin_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """校长端多维度签到看板"""
    # 1. 权限与身份判定
    username = str(current_user.username).strip().lower()
    employee_id = str(current_user.employee_id).strip().lower() if getattr(current_user, 'employee_id', None) else ""
    
    is_xz001 = (username == "xz001" or employee_id == "xz001")
    is_xz002 = (username == "xz002" or employee_id == "xz002")
    
    # 允许特定账号或具备特定角色的用户访问
    whitelisted = ["xz001", "xz002", "T15229628942"]
    is_test = (username in whitelisted) or (employee_id in whitelisted)
    is_authorized = (current_user.role in ["admin", "principal"]) or is_test or (current_user.view_scope == "all")
    
    if not is_authorized:
        # 如果是班主任身份，且试图看班主任看板，也允许
        if current_user.view_scope == "head_teacher" or current_user.role == "head_teacher":
            is_authorized = True
        else:
            raise HTTPException(status_code=403, detail="无权访问数据看板")

    # 2. 确定视角与标题
    dashboard_title = "清涧中学签到数据看板"
    force_headmaster_view = False
    
    # 逻辑：xz001 看全景，xz002 或 具备班主任视角的看班主任专版
    if is_xz001:
        dashboard_title = "清涧中学签到数据看板"
        force_headmaster_view = False
    elif is_xz002:
        dashboard_title = "清涧中学班主任签到数据看板"
        force_headmaster_view = True
    elif current_user.view_scope == "head_teacher" or current_user.role == "head_teacher":
        dashboard_title = "清涧中学班主任签到数据看板"
        force_headmaster_view = True
    else:
        # 默认全景 (admin/principal)
        dashboard_title = "清涧中学签到数据看板"
        force_headmaster_view = False

    try:
        if not checkin_date:
            checkin_date = date.today()

        # 3. 确定时间范围
        start_date = checkin_date
        end_date = checkin_date
        is_session_mode = (period == "session")
        
        if period == "week":
            start_date = checkin_date - timedelta(days=checkin_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == "month":
            start_date = checkin_date.replace(day=1)
            if start_date.month == 12:
                end_date = date(start_date.year, 12, 31)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
        elif period == "semester":
            start_date = checkin_date - timedelta(days=180)
            end_date = checkin_date

        # 4. 确定用户范围
        user_query = db.query(User).filter(User.is_active == True)
        if force_headmaster_view:
            user_query = user_query.filter(User.is_headmaster == True)
        
        # 排除管理员和当前用户
        teachers = user_query.filter(User.role != "admin", User.id != current_user.id).all()
        teacher_ids = [t.id for t in teachers]

        if not teacher_ids:
            return {
                "period": period,
                "dashboard_title": dashboard_title,
                "session_label": None,
                "date_range": f"{start_date.isoformat()} ~ {end_date.isoformat()}",
                "summary": {"total": 0, "normal_count": 0, "late_count": 0, "absent_count": 0, "leave_count": 0, "rate": 0},
                "categories": {"normal": [], "late": [], "absent": []},
                "debug_user": {
                    "u": username,
                    "e": employee_id,
                    "vis": dashboard_title
                }
            }

        # 5. 获取记录
        records_query = db.query(CheckinRecord).filter(
            CheckinRecord.user_id.in_(teacher_ids),
            CheckinRecord.checkin_date >= start_date,
            CheckinRecord.checkin_date <= end_date
        )
        
        current_slot = None
        if is_session_mode:
            from datetime import datetime
            now_time_obj = datetime.now().time()
            slots = get_user_time_slots(False)
            for s in reversed(slots):
                if now_time_obj >= s["start"]:
                    current_slot = s
                    break
            if not current_slot: current_slot = slots[0]
            
            records_query = records_query.filter(
                CheckinRecord.checkin_date == checkin_date,
                CheckinRecord.time_slot_id == current_slot["id"]
            )

        records = records_query.all()
        record_map = {}
        for r in records:
            if r.user_id not in record_map: record_map[r.user_id] = []
            record_map[r.user_id].append(r)

        # 6. 分类聚合
        categories = {"normal": [], "late": [], "absent": []}
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
                if not t_records or has_absent: categories["absent"].append(teacher_info)
                elif has_late: categories["late"].append(teacher_info)
                else: categories["normal"].append(teacher_info)

        total_teachers = len(teachers)
        summary = {
            "total": total_teachers,
            "normal_count": len(categories["normal"]),
            "late_count": len(categories["late"]),
            "absent_count": len(categories["absent"]),
            "leave_count": 0,
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
                "vis": dashboard_title,
                "is_xz001": is_xz001,
                "is_xz002": is_xz002,
                "force_headmaster": force_headmaster_view,
                "teacher_count": len(teachers)
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Principal dashboard error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
