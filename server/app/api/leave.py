"""请假API"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.leave import Leave
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/leave", tags=["请假"], redirect_slashes=False)


# ========================
# Pydantic 模型
# ========================

class LeaveCreate(BaseModel):
    leave_type: str
    start_time: datetime
    end_time: datetime
    reason: str


# ========================
# API 接口
# ========================

@router.post("")
def create_leave(
    data: LeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交请假申请"""
    leave = Leave(
        user_id=current_user.id,
        leave_type=data.leave_type,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
        status="pending"
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    
    return {
        "id": leave.id,
        "user_id": leave.user_id,
        "leave_type": leave.leave_type,
        "start_time": leave.start_time.isoformat() if leave.start_time else None,
        "end_time": leave.end_time.isoformat() if leave.end_time else None,
        "reason": leave.reason,
        "status": leave.status,
        "created_at": leave.created_at.isoformat() if leave.created_at else None,
    }


@router.get("/my")
def get_my_leaves(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的请假列表"""
    # 查询总数
    total = db.query(func.count(Leave.id)).filter(
        Leave.user_id == current_user.id
    ).scalar() or 0
    
    # 查询列表
    leaves = db.query(Leave).filter(
        Leave.user_id == current_user.id
    ).order_by(Leave.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for leave in leaves:
        result.append({
            "id": leave.id,
            "user_id": leave.user_id,
            "leave_type": leave.leave_type,
            "start_time": leave.start_time.isoformat() if leave.start_time else None,
            "end_time": leave.end_time.isoformat() if leave.end_time else None,
            "reason": leave.reason,
            "status": leave.status,
            "created_at": leave.created_at.isoformat() if leave.created_at else None,
        })
    
    return {
        "items": result,
        "total": total
    }


@router.get("/{leave_id}")
def get_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取请假详情"""
    leave = db.query(Leave).filter(
        Leave.id == leave_id,
        Leave.user_id == current_user.id
    ).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="请假记录不存在")
    
    return {
        "id": leave.id,
        "user_id": leave.user_id,
        "leave_type": leave.leave_type,
        "start_time": leave.start_time.isoformat() if leave.start_time else None,
        "end_time": leave.end_time.isoformat() if leave.end_time else None,
        "reason": leave.reason,
        "status": leave.status,
        "created_at": leave.created_at.isoformat() if leave.created_at else None,
    }
