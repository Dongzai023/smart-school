"""Device control API routes — manual lock/unlock/shutdown."""

import uuid
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.log import OperationLog
from app.models.user import User
from app.services.auth_service import require_admin
from app.ws.manager import ws_manager

router = APIRouter(prefix="/control", tags=["设备控制"])


class ControlRequest(BaseModel):
    device_ids: list[int]
    action: str  # lock_screen / unlock_screen / shutdown / reboot


class GroupControlRequest(BaseModel):
    group_id: int
    action: str


VALID_ACTIONS = {"lock_screen", "unlock_screen", "shutdown", "reboot"}


@router.post("/execute")
async def execute_control(
    req: ControlRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Send control command to specific devices."""
    if req.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"无效操作，可选: {VALID_ACTIONS}")

    results = {}
    for device_id in req.device_ids:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            results[device_id] = {"success": False, "message": "设备不存在"}
            continue

        task_id = uuid.uuid4().hex
        command = {
            "type": "command",
            "action": req.action,
            "task_id": task_id,
            "params": {},
        }
        success = await ws_manager.send_command_to_device(device_id, command)
        results[device_id] = {
            "success": success,
            "message": "指令已发送" if success else "设备离线，指令发送失败",
            "task_id": task_id,
        }

        # Log the operation
        log = OperationLog(
            device_id=device_id,
            user_id=admin.id,
            action=req.action,
            detail=f"手动操作: {req.action}",
            result="success" if success else "failed",
        )
        db.add(log)

    db.commit()
    return {"results": results}


@router.post("/execute-group")
async def execute_group_control(
    req: GroupControlRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Send control command to all devices in a group."""
    if req.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"无效操作，可选: {VALID_ACTIONS}")

    devices = db.query(Device).filter(Device.group_id == req.group_id).all()
    if not devices:
        raise HTTPException(status_code=404, detail="该分组下没有设备")

    results = {}
    for device in devices:
        task_id = uuid.uuid4().hex
        command = {
            "type": "command",
            "action": req.action,
            "task_id": task_id,
            "params": {},
        }
        success = await ws_manager.send_command_to_device(device.id, command)
        results[device.id] = {
            "success": success,
            "message": "指令已发送" if success else "设备离线",
            "task_id": task_id,
            "device_name": device.name,
        }

        log = OperationLog(
            device_id=device.id,
            user_id=admin.id,
            action=req.action,
            detail=f"分组操作: {req.action}",
            result="success" if success else "failed",
        )
        db.add(log)

    db.commit()
    return {"group_id": req.group_id, "results": results}
