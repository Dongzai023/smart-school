"""成就API"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models.checkin_record import CheckinRecord

router = APIRouter(prefix="/api/achievements", tags=["成就"])


@router.get("")
def get_achievements(db: Session = Depends(get_db), user_id: int = 1):
    """获取成就勋章"""
    # 计算各种成就
    today = datetime.now().date()
    
    # 统计签到次数
    total_checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).count()
    
    # 统计连续签到
    checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == user_id
    ).order_by(CheckinRecord.checkin_time.desc()).all()
    
    # 今日签到
    today_start = datetime.combine(today, datetime.min.time())
    today_checkin = any(c.checkin_time >= today_start for c in checkins)
    
    achievements = [
        {
            "id": 1,
            "name": "首次签到",
            "description": "完成第一次签到",
            "icon": "🎯",
            "unlocked": total_checkins >= 1
        },
        {
            "id": 2,
            "name": "坚持不懈",
            "description": "累计签到10次",
            "icon": "💪",
            "unlocked": total_checkins >= 10
        },
        {
            "id": 3,
            "name": "全勤之星",
            "description": "累计签到30次",
            "icon": "⭐",
            "unlocked": total_checkins >= 30
        },
        {
            "id": 4,
            "name": "签到达人",
            "description": "累计签到100次",
            "icon": "🏆",
            "unlocked": total_checkins >= 100
        },
        {
            "id": 5,
            "name": "今日打卡",
            "description": "今日已完成签到",
            "icon": "✅",
            "unlocked": today_checkin
        },
    ]
    
    return achievements
