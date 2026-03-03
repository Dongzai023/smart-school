"""成就API"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.checkin_record import CheckinRecord
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/achievements", tags=["成就"])


@router.get("")
def get_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成就勋章"""
    # 计算各种成就
    today = datetime.now().date()
    
    # 统计签到次数
    total_checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id
    ).count()
    
    # 统计连续签到天数
    checkins = db.query(CheckinRecord).filter(
        CheckinRecord.user_id == current_user.id
    ).order_by(CheckinRecord.checkin_time.desc()).all()
    
    # 今日签到
    today_start = datetime.combine(today, datetime.min.time())
    today_checkin = any(c.checkin_time >= today_start for c in checkins)
    
    # 统计连续签到
    consecutive_days = 0
    if checkins:
        checkin_dates = set()
        for c in checkins:
            if c.checkin_date:
                checkin_dates.add(c.checkin_date)
        
        checkin_dates = sorted(checkin_dates, reverse=True)
        if checkin_dates:
            consecutive_days = 1
            for i in range(len(checkin_dates) - 1):
                if (checkin_dates[i] - checkin_dates[i+1]).days == 1:
                    consecutive_days += 1
                else:
                    break
    
    achievements = [
        {
            "id": 1,
            "name": "首次签到",
            "description": "完成第一次签到",
            "emoji": "🎯",
            "unlocked": total_checkins >= 1
        },
        {
            "id": 2,
            "name": "坚持不懈",
            "description": "累计签到10次",
            "emoji": "💪",
            "unlocked": total_checkins >= 10
        },
        {
            "id": 3,
            "name": "全勤之星",
            "description": "累计签到30次",
            "emoji": "⭐",
            "unlocked": total_checkins >= 30
        },
        {
            "id": 4,
            "name": "签到达人",
            "description": "累计签到100次",
            "emoji": "🏆",
            "unlocked": total_checkins >= 100
        },
        {
            "id": 5,
            "name": "今日打卡",
            "description": "今日已完成签到",
            "emoji": "✅",
            "unlocked": today_checkin
        },
        {
            "id": 6,
            "name": "连续打卡",
            "description": f"连续签到{consecutive_days}天",
            "emoji": "🔥",
            "unlocked": consecutive_days >= 3,
            "progress": consecutive_days,
            "target": 3
        },
    ]
    
    # 统计已解锁数量
    unlocked_count = sum(1 for a in achievements if a["unlocked"])
    
    return {
        "items": achievements,
        "unlocked_count": unlocked_count,
        "total_count": len(achievements)
    }
