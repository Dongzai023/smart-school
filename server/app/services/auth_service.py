"""Authentication utilities: JWT tokens & password hashing."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    # 支持 pbkdf2_sha256 格式
    if hashed.startswith("$pbkdf2"):
        return pwd_context.verify(plain, hashed)
    # 兼容旧的 SHA256 格式
    import hashlib
    hashed_sha256 = hashlib.sha256(plain.encode()).hexdigest()
    return hashed_sha256 == hashed


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # Ensure 'sub' is a string for JWT compatibility
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT token and return the current user."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            print(f"DEBUG: Auth failed - 'sub' claim missing in token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
        user_id = int(user_id_raw)
    except (JWTError, ValueError) as e:
        print(f"DEBUG: Auth failed - Token decode error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证已过期或无效")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        print(f"DEBUG: Auth failed - User ID {user_id} not found in DB")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        print(f"DEBUG: Auth failed - User {user.username} is inactive")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已禁用")
    
    # Optional: Verify OpenID consistency if bound
    if getattr(user, 'wx_openid', None):
        oid_in_token = payload.get("oid")
        if oid_in_token and oid_in_token != user.wx_openid:
            print(f"DEBUG: Auth failed - OpenID mismatch for user {user.username}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="安全校验失败：微信账号不匹配")
    
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


def require_mgmt(current_user: User = Depends(get_current_user)) -> User:
    """Require admin or principal role."""
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理权限")
    return current_user
