"""User database model."""

from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Admin and teacher users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="登录用户名(工号)")
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="工号")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    real_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="真实姓名")
    nickname: Mapped[str] = mapped_column(String(50), default="", comment="昵称")
    department: Mapped[str] = mapped_column(String(100), default="", comment="部门/处室")
    department_group: Mapped[str] = mapped_column(String(100), default="", comment="所属教研组")
    email: Mapped[str] = mapped_column(String(100), default="", comment="邮箱")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="手机号")
    avatar_url: Mapped[str] = mapped_column(String(500), default="", comment="头像URL")
    gender: Mapped[str] = mapped_column(String(10), default="未知", comment="性别")
    teaching_subject: Mapped[str] = mapped_column(String(50), default="", comment="所教学科")
    grade: Mapped[str] = mapped_column(String(50), default="", comment="所属年级")
    class_name: Mapped[str] = mapped_column(String(50), default="", comment="所属班级")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="teacher", comment="角色: admin/teacher/head_teacher")
    is_headmaster: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否是班主任")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否认证教师")
    can_scan_unlock: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否可扫码解锁屏幕")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    wx_openid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=True, comment="绑定微信的OpenID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), nullable=True)
