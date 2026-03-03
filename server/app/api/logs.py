"""Operation log API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.log import OperationLog
from app.models.device import Device
from app.models.user import User
from app.services.auth_service import require_admin

router = APIRouter(prefix="/logs", tags=["操作日志"])


@router.get("")
def list_logs(
    device_id: Optional[int] = None,
    action: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List operation logs with pagination and filters."""
    query = db.query(OperationLog)
    if device_id:
        query = query.filter(OperationLog.device_id == device_id)
    if action:
        query = query.filter(OperationLog.action == action)

    total = query.count()
    logs = query.order_by(OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for log in logs:
        device = db.query(Device).filter(Device.id == log.device_id).first() if log.device_id else None
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        result.append({
            "id": log.id,
            "device_name": device.name if device else "-",
            "user_name": user.real_name if user else "系统",
            "action": log.action,
            "detail": log.detail,
            "result": log.result,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": result}
