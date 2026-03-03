"""用户扩展API"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import uuid

from app.database import get_db, get_db_session
from app.models.user import User
from app.models.checkin_record import CheckinRecord
from app.models.leave import Leave

router = APIRouter(prefix="/api/users", tags=["用户"])


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

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class UserStats(BaseModel):
    total_checkins: int
    on_time_count: int
    late_count: int
    pending_leaves: int


# ========================
# API 接口
# ========================

@router.get("/me", response_model=UserResponse)
def get_current_user(db: Session = Depends(get_db), user_id: int = 1):
    """获取当前用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    real_name: str | None = None,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """更新当前用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if real_name:
        user.real_name = real_name
    
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """修改密码"""
    from app.services.auth_service import verify_password, hash_password
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    user.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}


@router.get("/me/avatar")
def get_avatar(db: Session = Depends(get_db), user_id: int = 1):
    """获取头像URL"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    avatar_url = None
    if hasattr(user, 'avatar_url') and user.avatar_url:
        avatar_url = user.avatar_url
    
    return {"avatar_url": avatar_url}


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """上传头像"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 保存文件
    upload_dir = "/app/uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{user_id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    avatar_url = f"/uploads/avatars/{filename}"
    
    # 更新用户头像
    if hasattr(user, 'avatar_url'):
        user.avatar_url = avatar_url
        db.commit()
    
    return {"avatar_url": avatar_url}


@router.get("/me/activities")
def get_activities(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """获取最近活动"""
    # 获取签到记录作为活动
    checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).order_by(CheckinRecord.checkin_time.desc()).limit(limit).all()
    
    activities = []
    for c in checkins:
        activities.append({
            "type": "checkin",
            "time": c.checkin_time.isoformat(),
            "status": c.status,
            "message": f"签到: {c.status}"
        })
    
    return activities


@router.get("/me/stats", response_model=UserStats)
def get_user_stats(
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """获取用户统计"""
    # 全部签到统计
    total_checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).count()
    
    on_time_count = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.status == "signed"
    ).count()
    
    late_count = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.status == "late"
    ).count()
    
    # 待审批请假
    pending_leaves = db.query(Leave).filter(
        Leave.user_id == user_id,
        Leave.status == "pending"
    ).count()
    
    return {
        "total_checkins": total_checkins,
        "on_time_count": on_time_count,
        "late_count": late_count,
        "pending_leaves": pending_leaves
    }
