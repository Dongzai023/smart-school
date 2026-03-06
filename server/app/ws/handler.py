"""WebSocket endpoint handler for agent connections."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.device import Device
from app.models.lock_image import LockScreenImage
from app.ws.manager import ws_manager

logger = logging.getLogger("app.ws")

router = APIRouter()


def _get_device_by_key(db: Session, agent_key: str):
    """Look up a device by its agent key."""
    return db.query(Device).filter(Device.agent_key == agent_key).first()


def _get_default_image(db: Session, group_id):
    """Get the best matching lock screen image for a device group."""
    return db.query(LockScreenImage).filter(
        (LockScreenImage.assigned_group_id == group_id) |
        (LockScreenImage.assigned_group_id == None)
    ).order_by(
        LockScreenImage.is_default.desc(),
        LockScreenImage.created_at.desc()
    ).first()


@router.websocket("/ws/agent/{agent_key}")
async def agent_websocket(websocket: WebSocket, agent_key: str):
    """WebSocket endpoint for device agents to connect."""
    # Authenticate with a short-lived session
    db: Session = SessionLocal()
    try:
        device = _get_device_by_key(db, agent_key)
        if not device:
            await websocket.close(code=4001, reason="无效的Agent密钥")
            return
        device_id = device.id
        device_group_id = device.group_id

        await ws_manager.connect(websocket, agent_key, device_id)

        # Sync latest image on connect
        image = _get_default_image(db, device_group_id)
        if image:
            await websocket.send_json({
                "type": "command",
                "action": "sync_lock_image",
                "task_id": "on_connect_sync",
                "params": {
                    "image_id": image.id,
                    "image_url": f"/uploads/{image.file_name}",
                    "assigned_group_id": image.assigned_group_id,
                    "is_default": image.is_default,
                },
            })
    finally:
        db.close()

    # Main message loop — use short-lived DB sessions per operation
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Agent {agent_key}: 收到无效消息")
                continue

            msg_type = message.get("type")

            if msg_type == "heartbeat":
                db = SessionLocal()
                try:
                    device = db.query(Device).filter(Device.id == device_id).first()
                    if device:
                        device.last_heartbeat = datetime.now(timezone.utc)
                        device.online_status = True
                        info = message.get("device_info", {})
                        if info.get("ip"):
                            device.ip = info["ip"]
                        if info.get("agent_version"):
                            device.agent_version = info["agent_version"]
                        db.commit()
                finally:
                    db.close()
                await websocket.send_json({
                    "type": "heartbeat_ack",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "result":
                action = message.get("action", "")
                status = message.get("status")
                task_id = message.get("task_id", "")
                logger.info(f"Agent {agent_key}: 指令结果 action={action} status={status} task_id={task_id}")

                if action in ("lock_screen", "unlock_screen") and status == "success":
                    db = SessionLocal()
                    try:
                        device = db.query(Device).filter(Device.id == device_id).first()
                        if device:
                            device.lock_status = "locked" if action == "lock_screen" else "unlocked"
                            db.commit()
                    finally:
                        db.close()

            elif msg_type == "status_report":
                lock_status = message.get("lock_status")
                if lock_status:
                    db = SessionLocal()
                    try:
                        device = db.query(Device).filter(Device.id == device_id).first()
                        if device:
                            device.lock_status = lock_status
                            db.commit()
                    finally:
                        db.close()

    except WebSocketDisconnect:
        logger.info(f"Agent {agent_key}: WebSocket 断开")
    except Exception as e:
        logger.error(f"Agent {agent_key}: WebSocket 异常: {e}", exc_info=True)
    finally:
        ws_manager.disconnect(agent_key)
