"""用户扩展API"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import uuid

from app.database import get_db
from app.models.user import User
from app.models.checkin_record import CheckinRecord
from app.models.leave import Leave
from app.services.auth_service import get_current_user, hash_password, require_admin

router = APIRouter(prefix="/users", tags=["用户"])


# ========================
# Pydantic 模型
# ========================

class UserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    is_active: bool
    employee_id: str | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class UserProfileUpdate(BaseModel):
    nickname: str | None = None
    phone: str | None = None
    email: str | None = None
    gender: str | None = None
    teaching_subject: str | None = None
    department_group: str | None = None


class UserStats(BaseModel):
    total_checkins: int
    on_time_count: int
    late_count: int
    pending_leaves: int
    attendance_rate: float
    rank: int
    achievement_count: int


# ========================
# API 接口
# ========================

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "employee_id": current_user.employee_id or current_user.username,
        "name": current_user.real_name,
        "real_name": current_user.real_name,
        "nickname": current_user.nickname or "",
        "department": current_user.department or "",
        "department_group": current_user.department_group or "",
        "email": current_user.email or "",
        "phone": current_user.phone or "",
        "gender": current_user.gender or "未知",
        "teaching_subject": current_user.teaching_subject or "",
        "role": current_user.role,
        "is_headmaster": current_user.is_headmaster or current_user.role == "head_teacher",
        "is_verified": current_user.is_verified,
        "avatar_url": current_user.avatar_url or "",
    }


@router.put("/me")
def update_current_user(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前用户信息"""
    if data.nickname is not None:
        current_user.nickname = data.nickname
    if data.phone is not None:
        current_user.phone = data.phone
    if data.email is not None:
        current_user.email = data.email
    if data.gender is not None:
        current_user.gender = data.gender
    if data.teaching_subject is not None:
        current_user.teaching_subject = data.teaching_subject
    if data.department_group is not None:
        current_user.department_group = data.department_group
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "更新成功"}


@router.post("/me/password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    from app.services.auth_service import verify_password
    
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}


@router.get("/me/avatar")
def get_avatar(current_user: User = Depends(get_current_user)):
    """获取头像URL"""
    return {"avatar_url": current_user.avatar_url or ""}


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传头像"""
    # 保存文件
    upload_dir = "/app/uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    avatar_url = f"/uploads/avatars/{filename}"
    
    # 更新用户头像
    current_user.avatar_url = avatar_url
    db.commit()
    
    return {"avatar_url": avatar_url}


@router.get("/me/activities")
def get_activities(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取最近活动"""
    # 获取签到记录作为活动
    checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id
    ).order_by(CheckinRecord.checkin_time.desc()).limit(limit).all()
    
    activities = []
    for c in checkins:
        activities.append({
            "type": "checkin",
            "time": c.checkin_time.isoformat() if c.checkin_time else None,
            "date": c.checkin_date.isoformat() if c.checkin_date else None,
            "status": c.status,
            "message": f"签到: {c.time_slot_label}"
        })
    
    return activities


@router.get("/me/stats", response_model=UserStats)
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户统计"""
    # 全部签到统计
    total_checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id
    ).count()
    
    on_time_count = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id,
        CheckinRecord.status == "signed"
    ).count()
    
    late_count = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id,
        CheckinRecord.status == "late"
    ).count()
    
    # 待审批请假
    pending_leaves = db.query(Leave).filter(
        Leave.user_id == current_user.id,
        Leave.status == "pending"
    ).count()

    # 计算出勤率
    from sqlalchemy import func
    from app.api.statistics import get_user_time_slots, _get_date_range
    
    start_date, end_date = _get_date_range("semester")
    
    # 该时段内应签到次数
    work_days = sum(1 for i in range((end_date - start_date).days + 1)
                   if (start_date + timedelta(days=i)).weekday() < 5)
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    slot_count = len(get_user_time_slots(is_headmaster))
    expected = work_days * slot_count
    
    # 实际签到（正常+迟到）
    signed_in_period = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id,
        CheckinRecord.checkin_date >= start_date,
        CheckinRecord.checkin_date <= end_date,
        CheckinRecord.status.in_(["signed", "normal", "late"])
    ).count()
    
    attendance_rate = round(signed_in_period / expected * 100, 1) if expected > 0 else 0
    
    # 简单排名 (基于总签到数)
    rank_query = db.query(
        CheckinRecord.user_id,
        func.count(CheckinRecord.id).label("cnt")
    ).filter(
        CheckinRecord.status.in_(["signed", "normal", "late"])
    ).group_by(CheckinRecord.user_id).order_by(func.count(CheckinRecord.id).desc()).all()
    
    rank = 1
    for idx, r in enumerate(rank_query):
        if r.user_id == current_user.id:
            rank = idx + 1
            break
            
    # 成就数 (暂时用总签到天数/5作为模拟成就)
    achievement_count = total_checkins // 5
    
    return {
        "total_checkins": total_checkins,
        "on_time_count": on_time_count,
        "late_count": late_count,
        "pending_leaves": pending_leaves,
        "attendance_rate": attendance_rate,
        "rank": rank,
        "achievement_count": achievement_count
    }


# ========================
# 管理员管理接口
# ========================

class UserPermissionUpdate(BaseModel):
    can_scan_unlock: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    is_headmaster: Optional[bool] = None


@router.get("/admin/list")
def admin_list_users(
    page: int = 1,
    page_size: int = 50,
    role: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员获取用户列表"""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if department:
        query = query.filter(User.department == department)
    
    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "employee_id": getattr(u, 'employee_id', u.username),
                "real_name": u.real_name,
                "nickname": getattr(u, 'nickname', ''),
                "department": getattr(u, 'department', ''),
                "role": u.role,
                "is_headmaster": u.is_headmaster or u.role == "head_teacher",
                "is_verified": getattr(u, 'is_verified', True),
                "can_scan_unlock": getattr(u, 'can_scan_unlock', False),
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


class UserCreate(BaseModel):
    employee_id: str
    real_name: str
    nickname: Optional[str] = ""
    password: str
    department: Optional[str] = ""
    role: str = "teacher"


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    nickname: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    new_password: Optional[str] = None


@router.post("/admin/create")
def admin_create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员创建用户"""
    # 检查工号是否已存在
    existing = db.query(User).filter(
        (User.username == data.employee_id) | 
        (User.employee_id == data.employee_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该工号已存在")
    
    # 创建用户
    new_user = User(
        username=data.employee_id,
        employee_id=data.employee_id,
        real_name=data.real_name,
        nickname=data.nickname or "",
        password_hash=hash_password(data.password),
        department=data.department or "",
        role=data.role,
        is_active=True,
    )
    
    # 设置额外字段
    try:
        new_user.is_verified = True
        new_user.can_scan_unlock = False
    except Exception:
        pass
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"id": new_user.id, "username": new_user.username, "message": "用户创建成功"}


@router.put("/admin/{user_id}")
def admin_update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员更新用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if data.real_name is not None:
        user.real_name = data.real_name
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.department is not None:
        user.department = data.department
    if data.role is not None:
        user.role = data.role
    if data.new_password:
        user.password_hash = hash_password(data.new_password)
    
    db.commit()
    
    return {"message": "用户更新成功", "user_id": user_id}


@router.delete("/admin/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员账号")
    
    db.delete(user)
    db.commit()
    
    return {"message": "用户删除成功"}


@router.put("/admin/{user_id}/permissions")
def update_user_permissions(
    user_id: int,
    data: UserPermissionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员修改用户权限"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if data.can_scan_unlock is not None:
        user.can_scan_unlock = data.can_scan_unlock
    if data.is_verified is not None:
        user.is_verified = data.is_verified
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_headmaster is not None:
        user.is_headmaster = data.is_headmaster
    
    db.commit()
    
    return {"message": "权限更新成功", "user_id": user_id}


@router.put("/admin/{user_id}/unbind-wx")
def unbind_wx(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员解绑微信"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.wx_openid = None
    db.commit()
    
    return {"message": "微信解绑成功", "user_id": user_id}


@router.get("/admin/stats")
def admin_get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """管理员获取系统统计"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # 检查字段是否存在
    try:
        verified_users = db.query(User).filter(User.is_verified == True).count()
    except AttributeError:
        verified_users = total_users
    
    try:
        can_scan_unlock = db.query(User).filter(User.can_scan_unlock == True).count()
    except AttributeError:
        can_scan_unlock = 0
    
    # 今日签到统计
    from datetime import date, datetime
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_checkins = db.query(CheckinRecord).filter(
        CheckinRecord.checkin_time >= today_start
    ).count()
    
    # 请假统计 - 兼容不同字段名
    try:
        today_leaves = db.query(Leave).filter(
            Leave.created_at >= today_start
        ).count()
        pending_leaves = db.query(Leave).filter(Leave.status == "pending").count()
    except Exception:
        today_leaves = 0
        pending_leaves = 0
    
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "active_users": active_users,
        "can_scan_unlock": can_scan_unlock,
        "today_checkins": today_checkins,
        "today_leaves": today_leaves,
        "pending_leaves": pending_leaves
    }
