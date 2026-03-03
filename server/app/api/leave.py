"""请假API"""

from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.leave import Leave

router = APIRouter(prefix="/api/leave", tags=["请假"])


# ========================
# Pydantic 模型
# ========================

class LeaveCreate(BaseModel):
    leave_type: str  # sick/emergency/personal/other
    start_date: date
    end_date: date
    reason: str


class LeaveResponse(BaseModel):
    id: int
    user_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: str
    created_at: date

    class Config:
        from_attributes = True


# ========================
# API 接口
# ========================

@router.post("", response_model=LeaveResponse, status_code=201)
def create_leave(
    data: LeaveCreate,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """提交请假申请"""
    leave = Leave(
        user_id=user_id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        status="pending"
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/my")
def get_my_leaves(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """获取我的请假列表"""
    leaves = db.query(Leave).filter(
        Leave.user_id == user_id
    ).order_by(Leave.created_at.desc()).offset(skip).limit(limit).all()
    
    return leaves


@router.get("/{leave_id}")
def get_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """获取请假详情"""
    leave = db.query(Leave).filter(
        Leave.id == leave_id,
        Leave.user_id == user_id
    ).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="请假记录不存在")
    
    return leave
