"""Scan-to-unlock API route.

Teachers from the signature (attendance) system scan a QR code on the
Seewo lock screen.  This endpoint verifies their JWT token against the
signature system's secret key, checks teacher permissions in the
signature database, and sends an unlock command via WebSocket.
"""

import uuid
import logging
from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import SessionLocal
from app.models.device import Device
from app.models.log import OperationLog
from app.ws.manager import ws_manager

logger = logging.getLogger("app.scan_unlock")

router = APIRouter(prefix="/scan-unlock", tags=["扫码解锁"])

# ---- Signature DB engine (lazy init, read-only) ----
_sig_engine = None
_SigSession = None


def _get_sig_session():
    """Get a session to the signature (attendance) database."""
    global _sig_engine, _SigSession
    if _sig_engine is None:
        _sig_engine = create_engine(
            settings.SIGNATURE_DATABASE_URL,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
        )
        _SigSession = sessionmaker(bind=_sig_engine)
    return _SigSession()


# ---- Request / Response models ----

class ScanUnlockRequest(BaseModel):
    agent_key: str


class ScanUnlockResponse(BaseModel):
    success: bool
    message: str
    device_name: str = ""


# ---- Helper: verify signature JWT ----

def _verify_signature_token(token: str) -> dict:
    """Decode and verify a JWT issued by the signature system.

    Returns the decoded payload dict or raises HTTPException.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SIGNATURE_JWT_SECRET,
            algorithms=[settings.SIGNATURE_JWT_ALGORITHM],
        )
        teacher_id_raw = payload.get("sub")
        if teacher_id_raw is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        return {"teacher_id": int(teacher_id_raw)}
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="认证已过期或无效")


# ---- Helper: look up teacher in signature DB ----

def _get_teacher_info(teacher_id: int) -> dict | None:
    """Query the signature database for teacher info.

    Returns dict with name and is_verified, or None if not found.
    """
    session = _get_sig_session()
    try:
        result = session.execute(
            text("SELECT id, name, is_verified FROM teachers WHERE id = :tid"),
            {"tid": teacher_id},
        ).fetchone()
        if result is None:
            return None
        return {
            "id": result[0],
            "name": result[1],
            "is_verified": bool(result[2]),
        }
    finally:
        session.close()


# ---- Main endpoint ----

@router.post("", response_model=ScanUnlockResponse)
async def scan_unlock(
    req: ScanUnlockRequest,
    authorization: str = Header(..., description="Bearer <signature_jwt_token>"),
):
    """教师扫码解锁希沃一体机。

    1. 验证签到系统 JWT token
    2. 检查教师权限 (is_verified)
    3. 通过 WebSocket 发送解锁指令到设备
    """
    # 1. Extract token from header
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证格式")
    token = authorization[7:]

    # 2. Verify signature system JWT
    token_data = _verify_signature_token(token)
    teacher_id = token_data["teacher_id"]

    # 3. Look up teacher in signature DB
    teacher = _get_teacher_info(teacher_id)
    if teacher is None:
        raise HTTPException(status_code=401, detail="教师不存在")

    # 4. Check permission
    if not teacher["is_verified"]:
        logger.info(f"🚫 教师 {teacher['name']} (id={teacher_id}) 无解锁权限")
        return ScanUnlockResponse(
            success=False,
            message="你没有解锁权限",
        )

    # 5. Find device by agent_key
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.agent_key == req.agent_key).first()
        if not device:
            return ScanUnlockResponse(
                success=False,
                message="设备不存在",
            )

        # 6. Check if device is online
        if not ws_manager.is_device_online(device.id):
            return ScanUnlockResponse(
                success=False,
                message="设备不在线，请联系管理员",
                device_name=device.name,
            )

        # 7. Send unlock command
        task_id = uuid.uuid4().hex
        command = {
            "type": "command",
            "action": "unlock_screen",
            "task_id": task_id,
            "params": {"duration_minutes": 45},
        }
        success = await ws_manager.send_command_to_device(device.id, command)

        # 8. Log the operation
        log = OperationLog(
            device_id=device.id,
            action="unlock_screen",
            detail=f"扫码解锁: 教师{teacher['name']} (签到系统ID:{teacher_id})",
            result="success" if success else "failed",
        )
        db.add(log)
        db.commit()

        if success:
            logger.info(f"✅ 教师 {teacher['name']} 扫码解锁设备 {device.name} 成功")
            return ScanUnlockResponse(
                success=True,
                message=f"解锁成功",
                device_name=device.name,
            )
        else:
            logger.warning(f"⚠️ 教师 {teacher['name']} 扫码解锁设备 {device.name} 失败（指令发送失败）")
            return ScanUnlockResponse(
                success=False,
                message="解锁指令发送失败，请重试",
                device_name=device.name,
            )
    finally:
        db.close()
