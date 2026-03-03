"""Schedule database model."""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Schedule(Base):
    """Time-based schedule for lock/unlock/shutdown actions."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="策略名称")
    action: Mapped[str] = mapped_column(String(20), nullable=False, comment="动作: lock_screen/unlock_screen/shutdown")
    time: Mapped[datetime] = mapped_column(Time, nullable=False, comment="执行时间")
    weekdays: Mapped[str] = mapped_column(String(20), nullable=False, default="1,2,3,4,5", comment="星期: 1-7逗号分隔")
    target_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("device_groups.id"), nullable=True, comment="目标设备组")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    description: Mapped[str] = mapped_column(String(255), nullable=True, comment="描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
