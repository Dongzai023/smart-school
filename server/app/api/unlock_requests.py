"""Teacher unlock request API routes."""

import uuid
from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.log import UnlockRequest, OperationLog
from app.models.device import Device
from app.models.user import User
from app.services.auth_service import get_current_user, require_admin
from app.ws.manager import ws_manager

router = APIRouter(prefix="/unlock-requests", tags=["解锁申请"])


class UnlockRequestCreate(BaseModel):
    device_id: int
    reason: str
    duration_minutes: int = 45


class UnlockRequestReview(BaseModel):
    status: str  # approved / rejected


@router.get("")
def list_unlock_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List unlock requests. Admin sees all, teacher sees own."""
    query = db.query(UnlockRequest)
    if user.role != "admin":
        query = query.filter(UnlockRequest.teacher_id == user.id)
    if status:
        query = query.filter(UnlockRequest.status == status)
    requests = query.order_by(UnlockRequest.created_at.desc()).all()

    result = []
    for r in requests:
        device = db.query(Device).filter(Device.id == r.device_id).first()
        teacher = db.query(User).filter(User.id == r.teacher_id).first()
        result.append({
            "id": r.id,
            "teacher_name": teacher.real_name if teacher else "未知",
            "device_name": device.name if device else "未知",
            "device_id": r.device_id,
            "reason": r.reason,
            "duration_minutes": r.duration_minutes,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        })
    return result


@router.post("", status_code=201)
def create_unlock_request(
    req: UnlockRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Teacher submits an unlock request."""
    device = db.query(Device).filter(Device.id == req.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    unlock_req = UnlockRequest(
        teacher_id=user.id,
        device_id=req.device_id,
        reason=req.reason,
        duration_minutes=req.duration_minutes,
    )
    db.add(unlock_req)
    db.commit()
    db.refresh(unlock_req)
    return {"id": unlock_req.id, "status": unlock_req.status}


@router.put("/{request_id}/review")
async def review_unlock_request(
    request_id: int,
    req: UnlockRequestReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin approves or rejects an unlock request."""
    unlock_req = db.query(UnlockRequest).filter(UnlockRequest.id == request_id).first()
    if not unlock_req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if unlock_req.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")
    if req.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="状态只能是 approved 或 rejected")

    unlock_req.status = req.status
    unlock_req.reviewed_by = admin.id
    unlock_req.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # If approved, send unlock command to the device
    if req.status == "approved":
        task_id = uuid.uuid4().hex
        command = {
            "type": "command",
            "action": "unlock_screen",
            "task_id": task_id,
            "params": {"duration_minutes": unlock_req.duration_minutes},
        }
        success = await ws_manager.send_command_to_device(unlock_req.device_id, command)

        log = OperationLog(
            device_id=unlock_req.device_id,
            user_id=admin.id,
            action="unlock_screen",
            detail=f"审批教师解锁申请(申请ID:{request_id}), 时长:{unlock_req.duration_minutes}分钟",
            result="success" if success else "failed",
        )
        db.add(log)
        db.commit()

    return {"id": unlock_req.id, "status": unlock_req.status}
