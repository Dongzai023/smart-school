"""请假模型"""

from datetime import datetime, date
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Leave(Base):
    """请假记录"""

    __tablename__ = "leaves"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    leave_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="请假类型: 公假/事假/病假/年休假/婚假/产假/丧假/其他")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="请假原因")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="状态: pending/approved/rejected")
    approver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, comment="审批时间")
    remark: Mapped[str] = mapped_column(String(500), nullable=True, comment="审批备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
