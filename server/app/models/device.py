"""Device and DeviceGroup database models."""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceGroup(Base):
    """Device groups for organizing by classroom/building."""

    __tablename__ = "device_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="分组名称")
    building: Mapped[str] = mapped_column(String(100), nullable=True, comment="楼栋")
    floor: Mapped[str] = mapped_column(String(20), nullable=True, comment="楼层")
    description: Mapped[str] = mapped_column(String(255), nullable=True, comment="描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="group")


class Device(Base):
    """Seewo interactive flat panel device."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="设备名称")
    room_name: Mapped[str] = mapped_column(String(100), nullable=True, comment="教室名称")
    ip: Mapped[str] = mapped_column(String(45), nullable=True, comment="IP地址")
    mac: Mapped[str] = mapped_column(String(17), nullable=True, comment="MAC地址")
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("device_groups.id"), nullable=True, comment="所属分组")
    agent_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="Agent认证密钥")
    online_status: Mapped[bool] = mapped_column(default=False, comment="在线状态")
    lock_status: Mapped[str] = mapped_column(String(20), default="unlocked", comment="锁屏状态: locked/unlocked")
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=True, comment="最后心跳时间")
    agent_version: Mapped[str] = mapped_column(String(20), nullable=True, comment="Agent版本")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    group: Mapped["DeviceGroup"] = relationship("DeviceGroup", back_populates="devices")
