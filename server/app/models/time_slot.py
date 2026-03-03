"""签到时间槽模型"""

from datetime import datetime, time
from sqlalchemy import String, DateTime, Integer, Time, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimeSlot(Base):
    """签到时间段"""

    __tablename__ = "time_slots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False, comment="时段标签，如'早自习'、'午休'等")
    checkin_start: Mapped[time] = mapped_column(Time, nullable=False, comment="签到开始时间")
    normal_end: Mapped[time] = mapped_column(Time, nullable=False, comment="正常签到截止时间")
    late_end: Mapped[time] = mapped_column(Time, nullable=False, comment="迟到签到截止时间")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
