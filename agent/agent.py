"""Seewo Lock Screen Agent — main program.

Connects to the management server via WebSocket (WS or WSS),
receives commands, and executes lock/unlock/shutdown operations.
Supports cloud deployment over public internet with SSL.
"""

import os
import sys
import json
import time
import socket
import logging
import asyncio
import ssl
import threading
import traceback

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import yaml
import websockets

from lock_screen_window import LockScreenWindow
from image_sync import ImageSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("agent")


class SeewoAgent:
    """Main agent class that manages the WebSocket connection and command execution."""

    # Reconnect backoff parameters
    RECONNECT_BASE = 5
    RECONNECT_MAX = 60

    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.server_host = self.config["server"]["host"]
        self.server_port = self.config["server"].get("port", 443)
        self.use_ssl = self.config["server"].get("use_ssl", True)
        self.verify_ssl = self.config["server"].get("verify_ssl", True)
        self.agent_key = self.config["agent_key"]
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)

        # Build URLs based on SSL config
        http_scheme = "https" if self.use_ssl else "http"
        ws_scheme = "wss" if self.use_ssl else "ws"

        if self.use_ssl and self.server_port == 443:
            self.server_url = f"{http_scheme}://{self.server_host}"
            self.ws_url = f"{ws_scheme}://{self.server_host}/ws/agent/{self.agent_key}"
        else:
            self.server_url = f"{http_scheme}://{self.server_host}:{self.server_port}"
            self.ws_url = f"{ws_scheme}://{self.server_host}:{self.server_port}/ws/agent/{self.agent_key}"

        # SSL context
        self.ssl_context = None
        if self.use_ssl:
            self.ssl_context = ssl.create_default_context()
            if not self.verify_ssl:
                self.ssl_context.check_hostname = False
                self.ssl_context.verify_mode = ssl.CERT_NONE
                logger.warning("⚠️ SSL 证书验证已禁用")

        # Cache directory
        cache_dir = self.config.get("image_cache_dir", "./cache")
        os.makedirs(cache_dir, exist_ok=True)

        # Log file
        log_file = self.config.get("log_file", "./agent.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)

        # Components
        self.lock_window = LockScreenWindow()
        self.image_sync = ImageSync(self.server_url, cache_dir, verify_ssl=self.verify_ssl)
        self.ws = None
        self.running = True
        self._reconnect_delay = self.RECONNECT_BASE

    def _load_config(self, path):
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _is_connected(self):
        """Safely check if the WebSocket is connected (handles v12 and v14+)."""
        if not self.ws:
            return False
        # v12.0 legacy check
        if hasattr(self.ws, 'open'):
            return self.ws.open
        # v14.0+ check
        try:
            return self.ws.protocol.state.name == "OPEN"
        except (AttributeError, Exception):
            # Fallback: if we can't determine, assume closed if we hit an error
            return False

    def _get_device_info(self):
        """Collect current device information."""
        return {
            "ip": self._get_local_ip(),
            "hostname": socket.gethostname(),
            "agent_version": "1.1.0",
            "lock_status": "locked" if self.lock_window.is_locked else "unlocked",
        }

    def _get_local_ip(self):
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def _send_heartbeat(self):
        """Periodically send heartbeat to server."""
        while self.running:
            try:
                if self._is_connected():
                    msg = {
                        "type": "heartbeat",
                        "device_id": self.agent_key,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "device_info": self._get_device_info(),
                    }
                    await self.ws.send(json.dumps(msg))
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                break  # Exit heartbeat loop, let main loop handle reconnect
            await asyncio.sleep(self.heartbeat_interval)

    async def _handle_command(self, message):
        """Handle an incoming command from the server."""
        action = message.get("action")
        task_id = message.get("task_id", "")
        params = message.get("params", {})
        logger.info(f"🚀 收到指令: {action} (task_id={task_id})")

        result = {"type": "result", "task_id": task_id, "action": action, "status": "success", "message": ""}

        try:
            if action == "lock_screen":
                image_path = self.image_sync.get_latest_image()
                logger.info(f"锁屏图片: {image_path or '使用默认'}")
                self.lock_window.show(image_path if image_path else None)
                result["message"] = "锁屏成功"

            elif action == "unlock_screen":
                self.lock_window.hide()
                result["message"] = "解锁成功"
                duration = params.get("duration_minutes")
                if duration:
                    logger.info(f"临时解锁 {duration} 分钟后将自动锁屏")
                    asyncio.get_event_loop().call_later(
                        duration * 60,
                        lambda: self.lock_window.show(self.image_sync.get_latest_image())
                    )

            elif action == "shutdown":
                result["message"] = "即将关机"
                if self.ws:
                    await self.ws.send(json.dumps(result))
                await asyncio.sleep(2)
                os.system('shutdown /s /t 5 /c "管理系统远程关机"')
                return  # Don't send result again

            elif action == "reboot":
                result["message"] = "即将重启"
                if self.ws:
                    await self.ws.send(json.dumps(result))
                await asyncio.sleep(2)
                os.system('shutdown /r /t 5 /c "管理系统远程重启"')
                return

            elif action == "sync_lock_image":
                image_url = params.get("image_url")
                if image_url:
                    local_path = self.image_sync.download_image(image_url)
                    if local_path:
                        self.lock_window.update_image(local_path)
                        result["message"] = "锁屏画面同步成功"
                    else:
                        result["status"] = "failed"
                        result["message"] = "图片下载失败"

            else:
                result["status"] = "failed"
                result["message"] = f"未知指令: {action}"
                logger.warning(f"收到未知指令: {action}")

        except Exception as e:
            result["status"] = "failed"
            result["message"] = str(e)
            logger.error(f"指令执行异常 ({action}): {e}")
            logger.error(traceback.format_exc())

        # Send result back to server
        try:
            if self._is_connected():
                await self.ws.send(json.dumps(result))
        except Exception as e:
            logger.error(f"发送执行结果失败: {e}")

    async def connect(self):
        """Main connection loop with auto-reconnect and exponential backoff."""
        while self.running:
            try:
                logger.info(f"正在连接服务器: {self.ws_url}")
                async with websockets.connect(
                    self.ws_url,
                    ssl=self.ssl_context,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                ) as ws:
                    self.ws = ws
                    self._reconnect_delay = self.RECONNECT_BASE  # Reset on success
                    logger.info("✅ 服务器连接成功")

                    # Start heartbeat task
                    heartbeat_task = asyncio.create_task(self._send_heartbeat())

                    # Send initial status report
                    await ws.send(json.dumps({
                        "type": "status_report",
                        "lock_status": "locked" if self.lock_window.is_locked else "unlocked",
                        "device_info": self._get_device_info(),
                    }))

                    try:
                        async for raw_msg in ws:
                            try:
                                message = json.loads(raw_msg)
                                msg_type = message.get("type")
                                if msg_type == "command":
                                    await self._handle_command(message)
                                elif msg_type == "heartbeat_ack":
                                    pass  # Normal operation
                                else:
                                    logger.info(f"收到服务器消息: type={msg_type}")
                            except json.JSONDecodeError:
                                logger.warning(f"收到无效消息: {raw_msg[:100]}")
                    finally:
                        heartbeat_task.cancel()

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"连接断开: {e}")
            except Exception as e:
                logger.error(f"连接失败: {e}")

            self.ws = None
            logger.info(f"{self._reconnect_delay}秒后重连...")
            await asyncio.sleep(self._reconnect_delay)
            # Exponential backoff, capped at RECONNECT_MAX
            self._reconnect_delay = min(self._reconnect_delay * 1.5, self.RECONNECT_MAX)

    def run(self):
        """Start the agent."""
        logger.info("========== 希沃一体机管理Agent 启动 ==========")
        logger.info(f"服务器: {self.server_url}")
        logger.info(f"Agent密钥: {self.agent_key[:8]}...")
        logger.info(f"SSL验证: {'开启' if self.verify_ssl else '已禁用'}")
        logger.info(f"心跳间隔: {self.heartbeat_interval}秒")
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            logger.info("Agent 已停止")
            self.running = False


if __name__ == "__main__":
    config_path = "config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    agent = SeewoAgent(config_path)
    agent.run()
