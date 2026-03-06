"""签到API - 支持多角色多时段考勤"""

from datetime import datetime, date, time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.checkin_record import CheckinRecord
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/checkin", tags=["签到"])


# ========================
# 时间段配置（科任教师）
# ========================
TEACHER_TIME_SLOTS = [
    {"id": 1, "label": "上午", "start": time(7, 30), "normal_end": time(8, 10), "late_end": time(10, 10)},
    {"id": 2, "label": "中午", "start": time(10, 40), "normal_end": time(12, 0), "late_end": time(12, 0)},
    {"id": 3, "label": "下午", "start": time(13, 30), "normal_end": time(14, 10), "late_end": time(16, 0)},
    {"id": 4, "label": "晚自习", "start": time(16, 30), "normal_end": time(17, 30), "late_end": time(17, 30)},
]

# 班主任时间配置
HEAD_TEACHER_TIME_SLOTS = [
    {"id": 1, "label": "早自习", "start": time(6, 20), "normal_end": time(7, 30), "late_end": time(9, 20)},
    {"id": 2, "label": "下午", "start": time(13, 30), "normal_end": time(14, 10), "late_end": time(15, 10)},
    {"id": 3, "label": "傍晚", "start": time(16, 30), "normal_end": time(17, 40), "late_end": time(18, 0)},
    {"id": 4, "label": "晚自习", "start": time(18, 0), "normal_end": time(19, 20), "late_end": time(19, 20)},
]


def get_user_time_slots(is_headmaster: bool) -> List[dict]:
    """获取用户对应的时间段配置"""
    return HEAD_TEACHER_TIME_SLOTS if is_headmaster else TEACHER_TIME_SLOTS


def check_time_status(current_time: time, is_headmaster: bool) -> dict:
    """检查当前时间是否在签到时间内"""
    slots = get_user_time_slots(is_headmaster)
    now_minutes = current_time.hour * 60 + current_time.minute
    
    for slot in slots:
        start_minutes = slot["start"].hour * 60 + slot["start"].minute
        normal_minutes = slot["normal_end"].hour * 60 + slot["normal_end"].minute
        late_minutes = slot["late_end"].hour * 60 + slot["late_end"].minute
        
        if start_minutes <= now_minutes <= normal_minutes:
            return {
                "can_checkin": True,
                "message": "正常签到",
                "time_slot_id": slot["id"],
                "is_late": False
            }
        
        if normal_minutes < now_minutes <= late_minutes:
            return {
                "can_checkin": True,
                "message": "迟到",
                "time_slot_id": slot["id"],
                "is_late": True
            }
    
    return {
        "can_checkin": False,
        "message": "未在签到时间内",
        "time_slot_id": None,
        "is_late": False
    }


def get_today_status_for_user(db: Session, user_id: int, is_headmaster: bool) -> List[dict]:
    """获取用户今日所有时段的状态"""
    slots = get_user_time_slots(is_headmaster)
    today = date.today()
    
    # 获取用户今日已签到记录
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.checkin_date == today
    ).all()
    
    signed_slot_ids = {r.time_slot_id for r in records}
    
    items = []
    current_time = datetime.now().time()
    now_minutes = current_time.hour * 60 + current_time.minute
    
    for slot in slots:
        slot_id = slot["id"]
        start_minutes = slot["start"].hour * 60 + slot["start"].minute
        late_minutes = slot["late_end"].hour * 60 + slot["late_end"].minute
        
        # 判断状态
        if slot_id in signed_slot_ids:
            record = next(r for r in records if r.time_slot_id == slot_id)
            status = record.status
        elif now_minutes < start_minutes:
            status = "pending"  # 未到时间
        elif now_minutes > late_minutes:
            status = "absent"  # 已过期未签到
        else:
            status = "unsigned"  # 可以签到
        
        items.append({
            "id": slot_id,
            "status": status,
            "time_slot": {
                "id": slot_id,
                "label": slot["label"],
                "checkin_start": slot["start"].strftime("%H:%M:%S"),
                "normal_end": slot["normal_end"].strftime("%H:%M:%S"),
                "late_end": slot["late_end"].strftime("%H:%M:%S"),
            }
        })
    
    return items


# ========================
# Pydantic 模型
# ========================

class TimeSlotResponse(BaseModel):
    id: int
    label: str
    checkin_start: str
    normal_end: str
    late_end: str


class TodayCheckinItem(BaseModel):
    id: int
    status: str
    time_slot: dict


class TodayCheckinResponse(BaseModel):
    items: List[TodayCheckinItem]


class CheckinCreate(BaseModel):
    time_slot_id: int
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance: Optional[float] = None


class CheckinRecordResponse(BaseModel):
    id: int
    user_id: int
    time_slot_id: int
    checkin_time: datetime
    status: str
    location: Optional[str]


class CheckinStatusResponse(BaseModel):
    can_checkin: bool
    message: str
    time_slot_id: Optional[int] = None
    is_late: bool = False


# ========================
# API 接口
# ========================

@router.get("/today", response_model=TodayCheckinResponse)
def get_today_checkin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取今日签到安排"""
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    items = get_today_status_for_user(db, current_user.id, is_headmaster)
    return {"items": items}


@router.get("/status", response_model=CheckinStatusResponse)
def get_checkin_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前签到状态"""
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    current_time = datetime.now().time()
    return check_time_status(current_time, is_headmaster)


@router.post("", response_model=CheckinRecordResponse)
def do_checkin(
    data: CheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行签到"""
    is_headmaster = current_user.is_headmaster or current_user.role == "head_teacher"
    current_time = datetime.now().time()
    status_info = check_time_status(current_time, is_headmaster)
    
    if not status_info["can_checkin"]:
        raise HTTPException(status_code=400, detail=status_info["message"])
    
    # 检查是否已经签到过
    today = date.today()
    existing = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id,
        CheckinRecord.time_slot_id == data.time_slot_id,
        CheckinRecord.checkin_date == today
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="该时段已签到")
    
    # 获取时段标签
    slots = get_user_time_slots(is_headmaster)
    slot_label = next((s["label"] for s in slots if s["id"] == data.time_slot_id), "未知")
    
    # 创建签到记录
    record = CheckinRecord(
        user_id=current_user.id,
        time_slot_id=data.time_slot_id,
        time_slot_label=slot_label,
        checkin_date=today,
        checkin_time=datetime.now(),
        status="late" if status_info["is_late"] else "signed",
        location=data.location or "清涧中学",
        latitude=data.latitude,
        longitude=data.longitude,
        distance=data.distance
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
    current_user: User = Depends(get_current_user)
):
    """获取签到记录"""
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id
    ).order_by(CheckinRecord.checkin_time.desc()).offset(skip).limit(limit).all()
    
    return records
