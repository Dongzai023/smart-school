"""Authentication API routes."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models.user import User
from app.config import settings
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
    code: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class WxLoginRequest(BaseModel):
    code: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    real_name: str
    role: str = "teacher"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=status.HTTP_430_FORBIDDEN, detail="账号已被禁用")

    # WeChat OpenID Binding Logic
    if req.code and settings.WX_APPID and settings.WX_SECRET:
        async with httpx.AsyncClient() as client:
            url = "https://api.weixin.qq.com/sns/jscode2session"
            params = {
                "appid": settings.WX_APPID,
                "secret": settings.WX_SECRET,
                "js_code": req.code,
                "grant_type": "authorization_code",
            }
            try:
                resp = await client.get(url, params=params)
                data = resp.json()
                openid = data.get("openid")
                
                if openid:
                    # Check if this openid is already bound to another user
                    other_user = db.query(User).filter(User.wx_openid == openid, User.id != user.id).first()
                    if other_user:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN, 
                            detail=f"此微信已绑定账号({other_user.real_name})，不可重复绑定"
                        )

                    if not user.wx_openid:
                        # First time login on mini-program, bind openid
                        user.wx_openid = openid
                        db.commit()
                    elif user.wx_openid != openid:
                        # OpenID mismatch
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN, 
                            detail="当前微信账号与绑定的用户不一致，请联系管理员"
                        )
            except HTTPException:
                raise
            except Exception as e:
                # If WeChat API fails, we might still want to let them login but log the error
                # Or keep it strict. Here we log it.
                print(f"WeChat API Error: {e}")

    # Generate token with optional OpenID claim
    token_data = {"sub": user.id, "role": user.role}
    if req.code and 'openid' in locals() and openid:
        token_data["oid"] = openid
        
    token = create_access_token(data=token_data)
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


@router.post("/wx-login", response_model=LoginResponse)
async def wx_login(req: WxLoginRequest, db: Session = Depends(get_db)):
    """Silent login using WeChat OpenID."""
    if not settings.WX_APPID or not settings.WX_SECRET:
        raise HTTPException(status_code=400, detail="未配置微信相关信息")

    async with httpx.AsyncClient() as client:
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": settings.WX_APPID,
            "secret": settings.WX_SECRET,
            "js_code": req.code,
            "grant_type": "authorization_code",
        }
        try:
            resp = await client.get(url, params=params)
            data = resp.json()
            openid = data.get("openid")
            
            if not openid:
                raise HTTPException(status_code=400, detail="无法获取OpenID")
            
            # Find user with this openid
            user = db.query(User).filter(User.wx_openid == openid).first()
            if not user:
                raise HTTPException(status_code=404, detail="该微信未绑定账号，请先使用账号密码登录")
            
            if not user.is_active:
                raise HTTPException(status_code=430, detail="账号已被禁用")

            # Generate token
            token_data = {"sub": user.id, "role": user.role, "oid": openid}
            token = create_access_token(data=token_data)
            
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
        except HTTPException:
            raise
        except Exception as e:
            print(f"WeChat API Error: {e}")
            raise HTTPException(status_code=500, detail="微信登录异常，请稍后重试")


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
