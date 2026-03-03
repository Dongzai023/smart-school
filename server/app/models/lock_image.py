"""LockScreenImage database model."""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LockScreenImage(Base):
    """Lock screen background images uploadable by admin."""

    __tablename__ = "lock_screen_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="图片名称")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    file_size: Mapped[int] = mapped_column(Integer, nullable=True, comment="文件大小(bytes)")
    is_default: Mapped[bool] = mapped_column(default=False, comment="是否默认锁屏图")
    assigned_group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("device_groups.id"), nullable=True,
        comment="分配的设备组(null=全部)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
