"""签到记录模型"""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CheckinRecord(Base):
    """签到记录"""

    __tablename__ = "checkin_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    time_slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("time_slots.id"), nullable=False, comment="时间槽ID")
    checkin_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="签到时间")
    status: Mapped[str] = mapped_column(String(20), default="signed", comment="状态: signed/late/absent")
    location: Mapped[str] = mapped_column(String(255), nullable=True, comment="签到位置")
    latitude: Mapped[float] = mapped_column(Float, nullable=True, comment="纬度")
    longitude: Mapped[float] = mapped_column(Float, nullable=True, comment="经度")
    distance: Mapped[float] = mapped_column(Float, nullable=True, comment="距离(米)")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
