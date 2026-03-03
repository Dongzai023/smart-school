"""签到API"""

from datetime import datetime, date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.time_slot import TimeSlot
from app.models.checkin_record import CheckinRecord

router = APIRouter(prefix="/api/checkin", tags=["签到"])


# ========================
# Pydantic 模型
# ========================

class TimeSlotResponse(BaseModel):
    id: int
    label: str
    checkin_start: str
    normal_end: str
    late_end: str

    class Config:
        from_attributes = True


class TodayCheckinResponse(BaseModel):
    items: list


class CheckinCreate(BaseModel):
    time_slot_id: int
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CheckinRecordResponse(BaseModel):
    id: int
    user_id: int
    time_slot_id: int
    checkin_time: datetime
    status: str
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    distance: Optional[float]

    class Config:
        from_attributes = True


# ========================
# 依赖
# ========================

def get_current_user(db: Session = Depends(get_db), user_id: int = 1) -> User:
    """获取当前用户（临时实现）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# ========================
# API 接口
# ========================

@router.get("/today", response_model=TodayCheckinResponse)
def get_today_checkin(db: Session = Depends(get_db), user_id: int = 1):
    """获取今日签到安排"""
    today = date.today()
    weekday = today.isoweekday()  # 1-7 (周一到周日)
    
    # 获取所有活跃的时间槽
    time_slots = db.query(TimeSlot).filter(TimeSlot.is_active == True).all()
    
    # 获取用户今日已签到记录
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.checkin_time >= datetime.combine(today, time.min)
    ).all()
    
    signed_slot_ids = {r.time_slot_id for r in records}
    
    items = []
    for slot in time_slots:
        status = "unsigned"
        if slot.id in signed_slot_ids:
            # 找到对应的记录
            record = next(r for r in records if r.time_slot_id == slot.id)
            status = record.status
        
        items.append({
            "id": slot.id,
            "status": status,
            "time_slot": {
                "id": slot.id,
                "label": slot.label,
                "checkin_start": slot.checkin_start.strftime("%H:%M:%S") if slot.checkin_start else None,
                "normal_end": slot.normal_end.strftime("%H:%M:%S") if slot.normal_end else None,
                "late_end": slot.late_end.strftime("%H:%M:%S") if slot.late_end else None,
            }
        })
    
    return {"items": items}


@router.post("", response_model=CheckinRecordResponse)
def do_checkin(
    data: CheckinCreate,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """执行签到"""
    # 检查时间槽是否存在
    time_slot = db.query(TimeSlot).filter(TimeSlot.id == data.time_slot_id).first()
    if not time_slot:
        raise HTTPException(status_code=404, detail="签到时段不存在")
    
    # 检查是否已经签到过
    today_start = datetime.combine(date.today(), time.min)
    existing = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.time_slot_id == data.time_slot_id,
        CheckinRecord.checkin_time >= today_start
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="该时段已签到")
    
    # 检查是否迟到
    now = datetime.now().time()
    status = "signed"
    if now > time_slot.normal_end:
        status = "late"
    
    # 计算距离（如果有坐标）
    distance = None
    if data.latitude and data.longitude:
        # 这里可以添加距离计算逻辑
        # 默认通过前端传递的距离
        distance = data.location
    
    # 创建签到记录
    record = CheckinRecord(
        user_id=user_id,
        time_slot_id=data.time_slot_id,
        status=status,
        location=data.location,
        latitude=data.latitude,
        longitude=data.longitude,
        distance=distance
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return record


@router.get("/records")
def get_checkin_records(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """获取签到记录"""
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).order_by(CheckinRecord.checkin_time.desc()).offset(skip).limit(limit).all()
    
    return records
