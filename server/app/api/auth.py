"""Authentication API routes."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
)

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str | None = None
    employee_id: str | None = None
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class CreateUserRequest(BaseModel):
    username: str
    password: str
    real_name: str
    role: str = "teacher"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """User login."""
    # 支持 username 或 employee_id 登录
    if req.username:
        user = db.query(User).filter(User.username == req.username).first()
    elif req.employee_id:
        user = db.query(User).filter(User.employee_id == req.employee_id).first()
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供用户名")
    
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    token = create_access_token(data={"sub": user.id, "role": user.role})
    return LoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "employee_id": getattr(user, 'employee_id', user.username),
            "name": user.real_name,
            "real_name": user.real_name,
            "nickname": getattr(user, 'nickname', ''),
            "department": getattr(user, 'department', ''),
            "role": user.role,
            "avatar_url": getattr(user, 'avatar_url', '') or '',
            "is_headmaster": user.is_headmaster or user.role == "head_teacher",
            "is_verified": getattr(user, 'is_verified', True),
            "can_scan_unlock": getattr(user, 'can_scan_unlock', False),
        },
    )


@router.post("/users", status_code=201)
def create_user(req: CreateUserRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Create a new user (admin only)."""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        real_name=req.real_name,
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "real_name": user.real_name, "role": user.role}


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """List all users (admin only)."""
    users = db.query(User).all()
    return [
        {"id": u.id, "username": u.username, "real_name": u.real_name, "role": u.role, "is_active": u.is_active}
        for u in users
    ]


@router.put("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Enable/disable a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.put("/password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change own password."""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return {"id": current_user.id, "username": current_user.username, "real_name": current_user.real_name, "role": current_user.role}
