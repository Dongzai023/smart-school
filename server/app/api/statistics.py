"""统计API"""

from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

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
    is_mgmt = (current_user.role in ["admin", "principal"])
    is_auth_for_all = is_mgmt or (current_user.view_scope in ["all", "head_teacher", "subject_teacher"])
    
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
    records_query = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == target_user_id,
        CheckinRecord.checkin_date >= start_date,
        CheckinRecord.checkin_date <= end_date
    )
    
    # 获取当次时段 (如果是 session 模式)
    current_slot = None
    if period == "session":
        now_time_obj = datetime.now().time()
        # 获取基础时段配置来确定 session
        base_slots = get_user_time_slots(False)
        for s in reversed(base_slots):
            if now_time_obj >= s["start"]:
                current_slot = s
                break
        if not current_slot: current_slot = base_slots[0]
        
        # 核心修复：session 模式下只看当前时段的记录
        records_query = records_query.filter(CheckinRecord.time_slot_id == current_slot["id"])
        
    records = records_query.all()
    
    dedup_records = []
    seen_slots = set()
    for r in records:
        key = (r.checkin_date, r.time_slot_id)
        if key not in seen_slots:
            seen_slots.add(key)
            dedup_records.append(r)

    signed_count = sum(1 for r in dedup_records if r.status in ("signed", "normal"))
    late_count = sum(1 for r in dedup_records if r.status == "late")
    
    actual_valid = sum(1 for r in dedup_records if r.status in ("signed", "normal", "late"))
    
    # ========================================================
    # 核心修正：统一“总数/应到”判定逻辑
    # 一个时段被认为是“应到”的条件：
    # 1. 它是工作日且时间已过/已开始
    # 2. 或者该时段已经有了实际打卡记录（兼容加班/早到）
    # ========================================================
    now = datetime.now()
    past_expected_slots = 0
    signed_count = 0
    late_count = 0
    
    # 预先获取所有记录的日期时段集合以便判断
    record_keys = {(r.checkin_date, r.time_slot_id) for r in dedup_records if r.status in ("signed", "normal", "late")}
    
    if period == "session":
        # 本次时段逻辑
        if current_slot:
            is_expected = False
            # 条件1：工作日且时间已过 (session 模式下 current_slot 必然是当前/已开始)
            if date.today().weekday() < 5:
                is_expected = True
            # 条件2：已有打卡记录
            if (date.today(), current_slot["id"]) in record_keys:
                is_expected = True
            
            if is_expected:
                past_expected_slots = 1
    else:
        # 周期逻辑
        for i in range((end_date - start_date).days + 1):
            d = start_date + timedelta(days=i)
            if d > now.date(): continue
            
            for s in slots:
                is_expected = False
                # 条件1：工作日且时间已过
                if d.weekday() < 5:
                    if d < now.date() or (d == now.date() and now.time() >= s["start"]):
                        is_expected = True
                # 条件2：已有打卡记录
                if (d, s["id"]) in record_keys:
                    is_expected = True
                
                if is_expected:
                    past_expected_slots += 1

    signed_count = sum(1 for r in dedup_records if r.status in ("signed", "normal"))
    late_count = sum(1 for r in dedup_records if r.status == "late")
    absent_count = max(0, past_expected_slots - (signed_count + late_count))
    
    expected_total = past_expected_slots
    
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
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    user_id: Optional[int] = Query(None, description="目标用户ID (管理员权限)"),
    period: Optional[str] = Query(None, description="统计周期: week/month/semester"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取签到记录，按日期分组，支持按周期获取所有工作日"""
    target_user_id = current_user.id
    username = str(current_user.username).strip().lower()
    is_mgmt = (current_user.role in ["admin", "principal"])
    is_auth_for_all = is_mgmt or (current_user.view_scope in ["all", "head_teacher", "subject_teacher"])
    
    if user_id and is_auth_for_all:
        target_user_id = user_id
    elif user_id and user_id != current_user.id:
        logger.warning(f"get_records: User {username} (ID: {current_user.id}) denied access to user ID {user_id}")
    
    if period:
        # 按周期获取所有工作日
        start_date, end_date = _get_date_range(period)
        now = datetime.now()
        dates = []
        for i in range((end_date - start_date).days + 1):
            d = start_date + timedelta(days=i)
            if d.weekday() < 5 and d <= now.date():
                dates.append(d)
        dates.sort(reverse=True)
        # 支持对日期列表的分页
        total = len(dates)
        dates_to_show = dates[(page - 1) * page_size : page * page_size]
    else:
        # 传统模式：查询有签到记录的最近日期
        dates_query = db.query(
            func.distinct(CheckinRecord.checkin_date)
        ).filter(
            CheckinRecord.user_id == target_user_id
        ).order_by(
            CheckinRecord.checkin_date.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        dates_to_show = [d[0] for d in dates_query]
        total = db.query(
            func.count(func.distinct(CheckinRecord.checkin_date))
        ).filter(
            CheckinRecord.user_id == target_user_id
        ).scalar() or 0
    
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    
    records = []
    for d in dates_to_show:
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
        
        # 各时段签到详情
        # 判断目标用户是班主任还是科任老师
        target_user_for_slots = db.query(User).filter(User.id == target_user_id).first()
        is_hm = target_user_for_slots and (target_user_for_slots.is_headmaster or target_user_for_slots.role == "head_teacher")
        slots_config = get_user_time_slots(is_hm)
        
        slot_details = []
        record_by_slot = {r.time_slot_id: r for r in day_records}
        for slot in slots_config:
            slot_id = slot["id"]
            slot_label = slot["label"]
            rec = record_by_slot.get(slot_id)
            rec = record_by_slot.get(slot_id)
            if rec:
                slot_status = rec.status
                slot_time = rec.checkin_time.strftime("%H:%M") if rec.checkin_time else "--:--"
            else:
                # 核心逻辑：判断是否是“缺勤”还是“待打卡”
                now = datetime.now()
                is_expected = False
                # 判定为应到（缺勤）的条件
                if d.weekday() < 5:
                    if d < now.date() or (d == now.date() and now.time() >= slot["start"]):
                        is_expected = True
                
                if is_expected:
                    slot_status = "absent"
                else:
                    slot_status = "pending" # 待打卡 / 非工作日
                slot_time = None
            slot_details.append({
                "label": slot_label,
                "status": slot_status,
                "time": slot_time
            })
        
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
            "location": day_records[0].location if day_records else "清涧中学",
            "slots": slot_details
        })
    
    return {"records": records, "total": total}


# ========================
# 管理员API
# ========================

@router.get("/admin/overview")
def admin_get_overview(
    department: Optional[str] = Query(None),
    is_headmaster: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """管理员/校长获取全校签到概览"""
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(status_code=403, detail="需要管理权限")
    today = date.today()
    
    # 基础查询
    user_query = db.query(User).filter(User.is_active == True)
    if department:
        user_query = user_query.filter(User.department == department)
    if is_headmaster is True:
        user_query = user_query.filter((User.is_headmaster == True) | (User.role == "head_teacher"))
    if role:
        user_query = user_query.filter(User.role == role)
    total_users = user_query.count()
    
    # 今日已签到人数
    active_user_ids = [u.id for u in user_query.all()]
    if not active_user_ids:
        return {
            "total_users": 0,
            "signed_today": 0,
            "late_today": 0,
            "absent_today": 0,
            "attendance_rate": 0
        }

    signed_today = db.query(func.count(func.distinct(CheckinRecord.user_id))).filter(
        CheckinRecord.checkin_date == today,
        CheckinRecord.status.in_(["signed", "normal", "late"]),
        CheckinRecord.user_id.in_(active_user_ids)
    ).scalar() or 0
    
    # 今日迟到人数
    late_today = db.query(func.count(func.distinct(CheckinRecord.user_id))).filter(
        CheckinRecord.checkin_date == today,
        CheckinRecord.status == "late",
        CheckinRecord.user_id.in_(active_user_ids)
    ).scalar() or 0
    
    # 计算各类用户总数
    active_users = user_query.filter(User.is_active == True).count()
    verified_users = user_query.filter(User.is_verified == True).count()
    absent_today = total_users - signed_today
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
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
    is_headmaster: Optional[bool] = Query(None, description="是否只看班主任"),
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
    if is_headmaster is True:
        query = query.filter((User.is_headmaster == True) | (User.role == "head_teacher"))
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
            "view_scope": user.view_scope or "",
            "is_wechat_bound": bool(user.wx_openid),
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
    
    # 允许特定权限的用户访问
    is_authorized = (current_user.role in ["admin", "principal"]) or (current_user.view_scope in ["all", "head_teacher", "subject_teacher"])
    
    if not is_authorized:
        raise HTTPException(status_code=403, detail="无权访问数据看板")

    # 2. 确定视角与标题
    dashboard_title = "清涧中学签到数据看板"
    force_headmaster_view = False
    
    # 逻辑：view_scope 为 all 看全景，head_teacher 看班主任专版，subject_teacher 看科任老师专版
    if current_user.view_scope == "all":
        dashboard_title = "清涧中学签到数据看板"
        force_headmaster_view = False
    elif current_user.view_scope == "head_teacher":
        dashboard_title = "清涧中学班主任签到数据看板"
        force_headmaster_view = True
    elif current_user.view_scope == "subject_teacher":
        dashboard_title = "清涧中学科任老师签到数据看板"
        force_headmaster_view = False
        force_subject_teacher_view = True
    elif current_user.role in ["admin", "principal"]:
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
        force_subject_teacher_view = current_user.view_scope == "subject_teacher"
        user_query = db.query(User).filter(User.is_active == True)
        if force_headmaster_view:
            user_query = user_query.filter(or_(User.is_headmaster == True, User.role == "head_teacher"))
        elif force_subject_teacher_view:
            user_query = user_query.filter(User.is_headmaster == False, User.role != "head_teacher")
        
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
                "categories": {"normal": [], "late": [], "absent": [], "total": []},
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

        # 核心修复：对于 session/today 模式，获取今日所有时段的记录以计算准确的迟到次数
        if is_session_mode or period == "today":
            all_today_records = db.query(CheckinRecord).filter(
                CheckinRecord.user_id.in_(teacher_ids),
                CheckinRecord.checkin_date == checkin_date
            ).all()
            all_today_map = {}
            for r in all_today_records:
                if r.user_id not in all_today_map: all_today_map[r.user_id] = []
                all_today_map[r.user_id].append(r)
        else:
            all_today_map = None

        # 6. 获取累计总签到次数 (用于"查看全部"列表)
        lifetime_counts = db.query(
            CheckinRecord.user_id,
            func.count(CheckinRecord.id).label("total_cnt")
        ).filter(
            CheckinRecord.user_id.in_(teacher_ids),
            CheckinRecord.status.in_(["signed", "normal", "late"])
        ).group_by(CheckinRecord.user_id).all()
        lifetime_map = {r.user_id: r.total_cnt for r in lifetime_counts}

        # 7. 分类聚合
        categories = {"normal": [], "late": [], "absent": [], "total": []}
        from datetime import datetime
        now = datetime.now()
        for t in teachers:
            t_records = record_map.get(t.id, [])
            # 这里的 record_count 是当前周期内的次数
            period_count = len(t_records)
            # 这里的 lifetime_count 是所有时间的次数 (用于排序和列表展示)
            lifetime_count = lifetime_map.get(t.id, 0)
            is_hm = t.is_headmaster or getattr(t, 'role', '') == "head_teacher"
            teacher_slots = get_user_time_slots(is_hm)

            teacher_info_base = {
                "id": t.id,
                "real_name": t.real_name,
                "nickname": t.nickname,
                "avatar_url": t.avatar_url,
                "department": t.department or "校办公室",
                "is_headmaster": t.is_headmaster,
            }

            # 添加到"查看全部"分类，使用累计次数
            teacher_info_total = teacher_info_base.copy()
            teacher_info_total["record_count"] = lifetime_count
            categories["total"].append(teacher_info_total)

            # 核心修复：对于 session/today 模式，使用今日所有时段的记录计算迟到次数
            if is_session_mode or period == "today":
                records_for_stats = all_today_map.get(t.id, [])
            else:
                records_for_stats = t_records

            dedup_records = []
            seen_slots = set()
            for r in records_for_stats:
                key = (r.checkin_date, r.time_slot_id)
                if key not in seen_slots:
                    seen_slots.add(key)
                    dedup_records.append(r)

            has_late = any(r.status == "late" for r in dedup_records)
            has_signed = any(r.status in ("signed", "normal", "late") for r in dedup_records)

            # 核心修正：统一校长看板统计逻辑
            period_signed = 0
            period_late = 0
            period_expected = 0
            
            # 一个时段被认为是“应到”的条件：
            # 1. 它是工作日且时间已过/已开始
            # 2. 或者该时段已经有了实际打卡记录
            t_record_keys = {(r.checkin_date, r.time_slot_id) for r in t_records if r.status in ("signed", "normal", "late")}
            
            if is_session_mode:
                if current_slot:
                    is_expected = False
                    if checkin_date.weekday() < 5: is_expected = True
                    if (checkin_date, current_slot["id"]) in t_record_keys: is_expected = True
                    if is_expected: period_expected = 1
            else:
                for i in range((end_date - start_date).days + 1):
                    d = start_date + timedelta(days=i)
                    if d > now.date(): continue
                    for s in teacher_slots:
                        is_expected = False
                        if d.weekday() < 5:
                            if d < now.date() or (d == now.date() and now.time() >= s["start"]):
                                is_expected = True
                        if (d, s["id"]) in t_record_keys: is_expected = True
                        if is_expected: period_expected += 1

            period_signed = sum(1 for r in t_records if r.status in ("signed", "normal"))
            period_late = sum(1 for r in t_records if r.status == "late")
            period_absent = max(0, period_expected - (period_signed + period_late))

            teacher_info_period = teacher_info_base.copy()
            teacher_info_period["record_count"] = period_signed + period_late
            teacher_info_period["normal_count"] = period_signed
            teacher_info_period["late_count"] = period_late
            teacher_info_period["absent_count"] = period_absent

            has_absent = period_absent > 0
            has_late = period_late > 0

            # 调试日志：打印每个用户的记录信息
            if dedup_records and any(r.status == "late" for r in dedup_records):
                logger.info(f"User {t.real_name} (ID: {t.id}): total_records={len(dedup_records)}, late_count={teacher_info_period['late_count']}")
            
            if has_absent:
                categories["absent"].append(teacher_info_period)
            elif has_late:
                categories["late"].append(teacher_info_period)
            else:
                categories["normal"].append(teacher_info_period)


        # 按累计签到次数从高到低排列"查看全部"列表
        categories["total"].sort(key=lambda x: x["record_count"], reverse=True)

        total_teachers = len(teachers)
        summary = {
            "total": total_teachers,
            "normal_count": len(categories["normal"]),
            "late_count": len(categories["late"]),
            "absent_count": len(categories["absent"]),
            "leave_count": 0,
            "rate": round((len(categories["normal"]) + len(categories["late"])) / total_teachers * 100, 1) if total_teachers else 0
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
                "force_headmaster": force_headmaster_view,
                "teacher_count": len(teachers)
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Principal dashboard error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
