"""WebSocket connection manager for agent communication."""

import logging
from datetime import datetime, timezone

from fastapi import WebSocket

from app.database import SessionLocal
from app.models.device import Device

logger = logging.getLogger("app.ws.manager")


class ConnectionManager:
    """Manages WebSocket connections from device agents."""

    def __init__(self):
        # Map: agent_key -> WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}
        # Map: agent_key -> device_id
        self.agent_device_map: dict[str, int] = {}

    async def connect(self, websocket: WebSocket, agent_key: str, device_id: int):
        """Accept a new agent connection."""
        await websocket.accept()
        self.active_connections[agent_key] = websocket
        self.agent_device_map[agent_key] = device_id
        self._update_device_status(device_id, online=True)
        logger.info(f"✅ Agent {agent_key[:8]}... (device={device_id}) 已连接, 在线设备数={len(self.active_connections)}")

    def disconnect(self, agent_key: str):
        """Remove an agent connection."""
        self.active_connections.pop(agent_key, None)
        device_id = self.agent_device_map.pop(agent_key, None)
        if device_id:
            self._update_device_status(device_id, online=False)
        logger.info(f"❌ Agent {agent_key[:8]}... 已断开, 在线设备数={len(self.active_connections)}")

    async def send_command(self, agent_key: str, command: dict) -> bool:
        """Send a command to a specific agent."""
        ws = self.active_connections.get(agent_key)
        if ws:
            try:
                await ws.send_json(command)
                logger.info(f"📤 指令已发送 -> {agent_key[:8]}...: action={command.get('action')}")
                return True
            except Exception as e:
                logger.error(f"📤 指令发送失败 -> {agent_key[:8]}...: {e}")
                self.disconnect(agent_key)
                return False
        logger.warning(f"📤 指令发送失败: agent {agent_key[:8]}... 不在线")
        return False

    async def send_command_to_device(self, device_id: int, command: dict) -> bool:
        """Send a command to a device by its ID."""
        for key, did in self.agent_device_map.items():
            if did == device_id:
                return await self.send_command(key, command)
        logger.warning(f"📤 指令发送失败: device_id={device_id} 不在线")
        return False

    async def broadcast_to_group(self, group_id: int, command: dict, db):
        """Send a command to all devices in a group."""
        devices = db.query(Device).filter(Device.group_id == group_id).all()
        results = {}
        for device in devices:
            success = await self.send_command_to_device(device.id, command)
            results[device.id] = success
        return results

    async def broadcast_all(self, command: dict):
        """Send a command to all connected agents."""
        disconnected = []
        for key, ws in self.active_connections.items():
            try:
                await ws.send_json(command)
            except Exception:
                disconnected.append(key)
        for key in disconnected:
            self.disconnect(key)

    def get_online_device_ids(self) -> list[int]:
        """Return list of currently online device IDs."""
        return list(self.agent_device_map.values())

    def is_device_online(self, device_id: int) -> bool:
        """Check if a device is online."""
        return device_id in self.agent_device_map.values()

    def _update_device_status(self, device_id: int, online: bool):
        """Update device online status in the database."""
        db = SessionLocal()
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device:
                device.online_status = online
                if online:
                    device.last_heartbeat = datetime.now(timezone.utc)
                db.commit()
        except Exception as e:
            logger.error(f"更新设备状态失败: {e}")
        finally:
            db.close()


# Global connection manager instance
ws_manager = ConnectionManager()
