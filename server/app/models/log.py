"""UnlockRequest and OperationLog database models."""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UnlockRequest(Base):
    """Teacher temporary unlock request."""

    __tablename__ = "unlock_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="申请教师")
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, comment="目标设备")
    reason: Mapped[str] = mapped_column(String(500), nullable=False, comment="申请原因")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=45, comment="解锁时长(分钟)")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="状态: pending/approved/rejected/expired"
    )
    reviewed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, comment="审批时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OperationLog(Base):
    """System operation log for audit trail."""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=True, comment="设备ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="操作人")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    detail: Mapped[str] = mapped_column(Text, nullable=True, comment="操作详情")
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="success", comment="结果: success/failed")
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True, comment="操作IP")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
