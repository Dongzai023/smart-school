"""Schedule management API routes."""

from typing import Optional
from datetime import time

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schedule import Schedule
from app.models.user import User
from app.services.auth_service import require_admin
from app.services.scheduler import load_schedules

router = APIRouter(prefix="/schedules", tags=["时间策略"])


class ScheduleCreate(BaseModel):
    name: str
    action: str  # lock_screen / unlock_screen / shutdown
    time: str  # HH:MM format
    weekdays: str = "1,2,3,4,5"  # Monday-Friday
    target_group_id: Optional[int] = None
    description: Optional[str] = None


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    action: Optional[str] = None
    time: Optional[str] = None
    weekdays: Optional[str] = None
    target_group_id: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


VALID_ACTIONS = {"lock_screen", "unlock_screen", "shutdown"}


def _parse_time(time_str: str) -> time:
    """Parse HH:MM string to time object."""
    parts = time_str.split(":")
    return time(hour=int(parts[0]), minute=int(parts[1]))


@router.get("")
def list_schedules(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """List all schedules."""
    schedules = db.query(Schedule).order_by(Schedule.time).all()
    return [
        {
            "id": s.id, "name": s.name, "action": s.action,
            "time": s.time.strftime("%H:%M"), "weekdays": s.weekdays,
            "target_group_id": s.target_group_id, "is_active": s.is_active,
            "description": s.description,
        }
        for s in schedules
    ]


@router.post("", status_code=201)
def create_schedule(req: ScheduleCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Create a new schedule."""
    if req.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"无效的操作类型，可选: {VALID_ACTIONS}")
    schedule = Schedule(
        name=req.name,
        action=req.action,
        time=_parse_time(req.time),
        weekdays=req.weekdays,
        target_group_id=req.target_group_id,
        description=req.description,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    load_schedules()  # Reload scheduler
    return {"id": schedule.id, "name": schedule.name}


@router.put("/{schedule_id}")
def update_schedule(schedule_id: int, req: ScheduleUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Update a schedule."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="策略不存在")
    data = req.model_dump(exclude_unset=True)
    if "action" in data and data["action"] not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"无效的操作类型，可选: {VALID_ACTIONS}")
    if "time" in data and data["time"]:
        data["time"] = _parse_time(data["time"])
    for key, val in data.items():
        if val is not None:
            setattr(schedule, key, val)
    db.commit()
    load_schedules()  # Reload scheduler
    return {"id": schedule.id, "name": schedule.name}


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a schedule."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="策略不存在")
    db.delete(schedule)
    db.commit()
    load_schedules()  # Reload scheduler
    return {"message": "删除成功"}
