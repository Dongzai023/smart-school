"""Device and DeviceGroup management API routes."""

import uuid
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device, DeviceGroup
from app.models.user import User
from app.services.auth_service import require_admin, get_current_user
from app.ws.manager import ws_manager

router = APIRouter(prefix="/devices", tags=["设备管理"])


# ---------- Schemas ----------

class GroupCreate(BaseModel):
    name: str
    building: Optional[str] = None
    floor: Optional[str] = None
    description: Optional[str] = None


class DeviceCreate(BaseModel):
    name: str
    room_name: Optional[str] = None
    ip: Optional[str] = None
    mac: Optional[str] = None
    group_id: Optional[int] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    room_name: Optional[str] = None
    ip: Optional[str] = None
    mac: Optional[str] = None
    group_id: Optional[int] = None


# ---------- Device Groups ----------

@router.get("/groups")
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List all device groups."""
    groups = db.query(DeviceGroup).all()
    return [
        {
            "id": g.id, "name": g.name, "building": g.building,
            "floor": g.floor, "description": g.description,
            "device_count": len(g.devices),
        }
        for g in groups
    ]


@router.post("/groups", status_code=201)
def create_group(req: GroupCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Create a device group."""
    group = DeviceGroup(**req.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"id": group.id, "name": group.name}


@router.put("/groups/{group_id}")
def update_group(group_id: int, req: GroupCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Update a device group."""
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    for key, val in req.model_dump(exclude_unset=True).items():
        setattr(group, key, val)
    db.commit()
    return {"id": group.id, "name": group.name}


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a device group."""
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    if group.devices:
        raise HTTPException(status_code=400, detail="分组下还有设备，无法删除")
    db.delete(group)
    db.commit()
    return {"message": "删除成功"}


# ---------- Devices ----------

@router.get("")
def list_devices(
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all devices, optionally filtered by group."""
    query = db.query(Device)
    if group_id:
        query = query.filter(Device.group_id == group_id)
    devices = query.all()
    return [
        {
            "id": d.id, "name": d.name, "room_name": d.room_name,
            "ip": d.ip, "mac": d.mac, "group_id": d.group_id,
            "agent_key": d.agent_key, "online_status": d.online_status,
            "lock_status": d.lock_status,
            "last_heartbeat": d.last_heartbeat.isoformat() if d.last_heartbeat else None,
            "agent_version": d.agent_version,
        }
        for d in devices
    ]


@router.post("", status_code=201)
def create_device(req: DeviceCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Create a new device and generate an agent key."""
    agent_key = uuid.uuid4().hex
    device = Device(agent_key=agent_key, **req.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return {
        "id": device.id, "name": device.name, "agent_key": device.agent_key,
        "room_name": device.room_name,
    }


@router.put("/{device_id}")
def update_device(device_id: int, req: DeviceUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Update device info."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    for key, val in req.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(device, key, val)
    db.commit()
    return {"id": device.id, "name": device.name}


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    db.delete(device)
    db.commit()
    return {"message": "删除成功"}


@router.get("/status/summary")
def device_status_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get summary of device statuses for dashboard."""
    total = db.query(Device).count()
    online = db.query(Device).filter(Device.online_status == True).count()
    locked = db.query(Device).filter(Device.lock_status == "locked").count()
    return {
        "total": total,
        "online": online,
        "offline": total - online,
        "locked": locked,
        "unlocked": total - locked,
    }
