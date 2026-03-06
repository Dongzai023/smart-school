"""扫码解锁API - 通过微信扫码解锁希沃一体机屏幕"""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.device import Device
from app.models.log import OperationLog
from app.services.auth_service import get_current_user
from app.ws.manager import ws_manager

router = APIRouter(prefix="/unlock", tags=["扫码解锁"])


class ScanUnlockRequest(BaseModel):
    device_id: int


class ScanUnlockResponse(BaseModel):
    success: bool
    message: str
    device_name: str = None
    duration_minutes: int = None


@router.post("", response_model=ScanUnlockResponse)
async def scan_unlock(
    req: ScanUnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    微信扫码解锁屏幕接口
    
    只有以下用户可以解锁：
    1. 管理员 (admin)
    2. 已认证教师 (is_verified=True)
    3. 有扫码解锁权限的用户 (can_scan_unlock=True)
    """
    
    # 获取设备信息
    device = db.query(Device).filter(Device.id == req.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 检查用户权限
    can_unlock = (
        current_user.role == "admin" or 
        getattr(current_user, 'is_verified', False) or 
        getattr(current_user, 'can_scan_unlock', False)
    )
    
    if not can_unlock:
        # 记录尝试解锁的日志
        log = OperationLog(
            device_id=device.id,
            user_id=current_user.id,
            action="scan_unlock_failed",
            detail=f"用户 {current_user.real_name}({current_user.username}) 尝试解锁屏幕但无权限",
            result="denied"
        )
        db.add(log)
        db.commit()
        
        return ScanUnlockResponse(
            success=False,
            message="请联系管理员授权扫码功能！",
            device_name=device.name
        )
    
    # 有权限，解锁屏幕
    # 默认解锁时长：班主任60分钟，普通教师45分钟
    if current_user.role == "head_teacher" or current_user.is_headmaster:
        duration_minutes = 60
    else:
        duration_minutes = 45
    
    task_id = uuid.uuid4().hex
    command = {
        "type": "command",
        "action": "unlock_screen",
        "task_id": task_id,
        "params": {"duration_minutes": duration_minutes},
    }
    
    # 发送解锁命令到设备
    success = await ws_manager.send_command_to_device(device.id, command)
    
    # 记录解锁日志
    log = OperationLog(
        device_id=device.id,
        user_id=current_user.id,
        action="scan_unlock",
        detail=f"用户 {current_user.real_name}({current_user.username}) 通过扫码解锁屏幕，时长:{duration_minutes}分钟",
        result="success" if success else "failed"
    )
    db.add(log)
    db.commit()
    
    if success:
        return ScanUnlockResponse(
            success=True,
            message=f"屏幕已解锁，欢迎 {current_user.real_name} 老师！",
            device_name=device.name,
            duration_minutes=duration_minutes
        )
    else:
        return ScanUnlockResponse(
            success=False,
            message="解锁命令发送失败，请稍后重试",
            device_name=device.name
        )


@router.get("/device/{device_id}")
def get_device_unlock_info(
    device_id: int,
    db: Session = Depends(get_db)
):
    """获取设备解锁信息（小程序扫码前调用）"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    return {
        "device_id": device.id,
        "device_name": device.name,
        "room_name": device.room_name,
        "status": device.lock_status
    }
