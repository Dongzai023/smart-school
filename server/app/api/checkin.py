"""签到API - 支持多角色多时段考勤"""

from datetime import datetime, date, time, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.time_slot import TimeSlot
from app.models.checkin_record import CheckinRecord

router = APIRouter(prefix="/api/checkin", tags=["签到"])


# ========================
# 时间段配置（科任教师）
# ========================
TEACHER_TIME_SLOTS = [
    # (开始, 正常结束, 迟到结束, 标签)
    (time(7, 30), time(8, 10), time(10, 10), "上午"),      # 07:30-08:10正常, 08:10-10:10迟到
    (time(10, 40), time(12, 0), time(12, 0), "中午"),    # 10:40-12:00正常
    (time(13, 30), time(14, 10), time(16, 0), "下午"),    # 13:30-14:10正常, 14:10-16:00迟到
    (time(16, 30), time(17, 30), time(17, 30), "晚自习"),  # 16:30-17:30正常
]

# 班主任时间配置
HEAD_TEACHER_TIME_SLOTS = [
    (time(6, 20), time(7, 30), time(9, 20), "早自习"),    # 06:20-07:30正常, 07:30-09:20迟到
    (time(13, 30), time(14, 10), time(15, 10), "下午"),   # 13:30-14:10正常, 14:10-15:10迟到
    (time(16, 30), time(17, 40), time(18, 0), "傍晚"),    # 16:30-17:40正常
    (time(18, 0), time(19, 20), time(19, 20), "晚自习"),  # 18:00-19:20正常
]


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
    latitude: Optional[float]
    longitude: Optional[float]
    distance: Optional[float]

    class Config:
        from_attributes = True


class CheckinStatusResponse(BaseModel):
    can_checkin: bool
    message: str
    time_slot_id: Optional[int] = None
    is_late: bool = False


# ========================
# 辅助函数
# ========================

def get_user_time_slots(is_headmaster: bool) -> List[tuple]:
    """获取用户对应的时间段配置"""
    return HEAD_TEACHER_TIME_SLOTS if is_headmaster else TEACHER_TIME_SLOTS


def check_time_status(current_time: time, is_headmaster: bool) -> dict:
    """
    检查当前时间是否在签到时间内
    返回: {can_checkin, message, time_slot_id, is_late}
    """
    slots = get_user_time_slots(is_headmaster)
    now_minutes = current_time.hour * 60 + current_time.minute
    
    # 科任教师提示信息
    teacher_hints = {
        "before": "未到签到时间",
        "normal": "正常",
        "late": "迟到",
        "after": "未在签到时间内"
    }
    
    # 班主任提示信息
    head_teacher_hints = {
        "before": "未到签到时间",
        "normal": "正常",
        "late": "迟到", 
        "after": "未在签到时间内"
    }
    
    hints = head_teacher_hints if is_headmaster else teacher_hints
    
    for idx, (start, normal_end, late_end, label) in enumerate(slots):
        start_minutes = start.hour * 60 + start.minute
        normal_minutes = normal_end.hour * 60 + normal_end.minute
        late_minutes = late_end.hour * 60 + late_end.minute
        
        # 在正常签到时段
        if start_minutes <= now_minutes <= normal_minutes:
            return {
                "can_checkin": True,
                "message": hints["normal"],
                "time_slot_id": idx + 1,
                "is_late": False
            }
        
        # 在迟到时段
        if normal_minutes < now_minutes <= late_minutes:
            return {
                "can_checkin": True,
                "message": hints["late"],
                "time_slot_id": idx + 1,
                "is_late": True
            }
        
        # 如果当前时间已经过了这个时段的迟到截止时间
        if now_minutes > late_minutes:
            continue
        
        # 如果当前时间还没到第一个时段的开始时间
        if now_minutes < start_minutes:
            return {
                "can_checkin": False,
                "message": hints["before"],
                "time_slot_id": None,
                "is_late": False
            }
    
    # 所有时段都过了
    return {
        "can_checkin": False,
        "message": hints["after"],
        "time_slot_id": None,
        "is_late": False
    }


def get_today_status_for_user(db: Session, user_id: int) -> List[dict]:
    """获取用户今日所有时段的状态"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    is_headmaster = user.is_headmaster or user.role == "head_teacher"
    slots = get_user_time_slots(is_headmaster)
    
    # 获取用户今日已签到记录
    today_start = datetime.combine(date.today(), time.min)
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.checkin_time >= today_start
    ).all()
    
    signed_slot_ids = {r.time_slot_id for r in records}
    
    items = []
    current_time = datetime.now().time()
    now_minutes = current_time.hour * 60 + current_time.minute
    
    for idx, (start, normal_end, late_end, label) in enumerate(slots):
        slot_id = idx + 1
        start_minutes = start.hour * 60 + start.minute
        normal_minutes = normal_end.hour * 60 + normal_end.minute
        late_minutes = late_end.hour * 60 + late_end.minute
        
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
                "label": label,
                "checkin_start": start.strftime("%H:%M:%S"),
                "normal_end": normal_end.strftime("%H:%M:%S"),
                "late_end": late_end.strftime("%H:%M:%S"),
            }
        })
    
    return items


# ========================
# API 接口
# ========================

@router.get("/today", response_model=TodayCheckinResponse)
def get_today_checkin(
    db: Session = Depends(get_db),
    user_id: int = Query(1, description="用户ID")
):
    """获取今日签到安排"""
    items = get_today_status_for_user(db, user_id)
    return {"items": items}


@router.get("/status", response_model=CheckinStatusResponse)
def get_checkin_status(
    db: Session = Depends(get_db),
    user_id: int = Query(1, description="用户ID")
):
    """获取当前签到状态（用于小程序实时检查）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    is_headmaster = user.is_headmaster or user.role == "head_teacher"
    current_time = datetime.now().time()
    
    return check_time_status(current_time, is_headmaster)


@router.post("", response_model=CheckinRecordResponse)
def do_checkin(
    data: CheckinCreate,
    db: Session = Depends(get_db),
    user_id: int = Query(1, description="用户ID")
):
    """执行签到"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查签到状态
    is_headmaster = user.is_headmaster or user.role == "head_teacher"
    current_time = datetime.now().time()
    status_info = check_time_status(current_time, is_headmaster)
    
    if not status_info["can_checkin"]:
        raise HTTPException(status_code=400, detail=status_info["message"])
    
    # 检查是否已经签到过
    today_start = datetime.combine(date.today(), time.min)
    existing = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.time_slot_id == data.time_slot_id,
        CheckinRecord.checkin_time >= today_start
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="该时段已签到")
    
    # 获取时段标签
    slots = get_user_time_slots(is_headmaster)
    slot_label = slots[data.time_slot_id - 1][3] if data.time_slot_id <= len(slots) else "未知"
    
    # 创建签到记录
    record = CheckinRecord(
        user_id=user_id,
        time_slot_id=data.time_slot_id,
        time_slot_label=slot_label,
        status="late" if status_info["is_late"] else "signed",
        location=data.location,
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
    user_id: int = Query(1, description="用户ID")
):
    """获取签到记录"""
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).order_by(CheckinRecord.checkin_time.desc()).offset(skip).limit(limit).all()
    
    return records
