"""签到记录模型"""

from datetime import datetime, date
from sqlalchemy import String, DateTime, Integer, Float, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CheckinRecord(Base):
    """签到记录"""

    __tablename__ = "checkin_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    time_slot_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="时间槽ID(代码配置)")
    time_slot_label: Mapped[str] = mapped_column(String(50), nullable=True, comment="时间槽标签")
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="签到日期")
    checkin_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="签到时间")
    status: Mapped[str] = mapped_column(String(20), default="signed", comment="状态: signed/late/absent")
    location: Mapped[str] = mapped_column(String(255), nullable=True, comment="签到位置")
    latitude: Mapped[float] = mapped_column(Float, nullable=True, comment="纬度")
    longitude: Mapped[float] = mapped_column(Float, nullable=True, comment="经度")
    distance: Mapped[float] = mapped_column(Float, nullable=True, comment="距离(米)")
    remark: Mapped[str] = mapped_column(String(500), nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")
