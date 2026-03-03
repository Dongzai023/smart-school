"""统计API"""

from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.checkin_record import CheckinRecord
from app.models.time_slot import TimeSlot

router = APIRouter(prefix="/api/statistics", tags=["统计"])


@router.get("/overview")
def get_overview(period: str = "week", db: Session = Depends(get_db), user_id: int = 1):
    """获取统计概览"""
    today = date.today()
    
    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=7)
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    # 获取该用户的签到记录
    records = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id,
        CheckinRecord.checkin_time >= start_datetime
    ).all()
    
    total = len(records)
    on_time = len([r for r in records if r.status == "signed"])
    late = len([r for r in records if r.status == "late"])
    absent = 0  # 可以根据时间槽数量计算
    
    return {
        "total": total,
        "on_time": on_time,
        "late": late,
        "absent": absent,
        "rate": round((on_time / total * 100) if total > 0 else 0, 1)
    }


@router.get("/trend")
def get_trend(period: str = "week", db: Session = Depends(get_db), user_id: int = 1):
    """获取签到趋势"""
    today = date.today()
    days = 7 if period == "week" else 30
    
    result = []
    for i in range(days):
        day = today - timedelta(days=days - i - 1)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        count = db.query(CheckinRecord).filter(
            CheckinRecord.user_id == user_id,
            CheckinRecord.checkin_time >= day_start,
            CheckinRecord.checkin_time <= day_end
        ).count()
        
        result.append({
            "date": day.strftime("%Y-%m-%d"),
            "count": count
        })
    
    return result


@router.get("/timeslot")
def get_timeslot_stats(period: str = "week", db: Session = Depends(get_db), user_id: int = 1):
    """获取时段分析"""
    today = date.today()
    start_date = today - timedelta(days=7 if period == "week" else 30)
    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    # 获取该用户在各时间段的签到统计
    time_slots = db.query(TimeSlot).all()
    
    result = []
    for slot in time_slots:
        count = db.query(CheckinRecord).filter(
            CheckinRecord.user_id == user_id,
            CheckinRecord.time_slot_id == slot.id,
            CheckinRecord.checkin_time >= start_datetime
        ).count()
        
        result.append({
            "label": slot.label,
            "count": count
        })
    
    return result


@router.get("/records")
def get_records(limit: int = 10, db: Session = Depends(get_db), user_id: int = 1):
    """获取最近签到记录"""
    records = db.query(CheckinRecord, TimeSlot).join(
        TimeSlot, CheckinRecord.time_slot_id == TimeSlot.id
    ).filter(
        CheckinRecord.user_id == user_id
    ).order_by(CheckinRecord.checkin_time.desc()).limit(limit).all()
    
    result = []
    for record, slot in records:
        result.append({
            "id": record.id,
            "time_slot_label": slot.label,
            "checkin_time": record.checkin_time.isoformat(),
            "status": record.status,
            "location": record.location
        })
    
    return result
