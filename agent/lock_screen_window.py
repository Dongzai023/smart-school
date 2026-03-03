"""Lock screen full-screen overlay window.

Uses tkinter to create a frameless, topmost, fullscreen window
that displays the lock screen background image with a QR code
for WeChat scan-to-unlock.
"""

import os
import io
import threading
import time
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import logging

try:
    import qrcode
except ImportError:
    qrcode = None

logger = logging.getLogger("agent.lock_window")

# QR code URL template  —  teachers scan this with WeChat
QR_URL_TEMPLATE = "https://www.qjzxmd.cn/scan-unlock?device_id={agent_key}"

# 图片轮播间隔（秒）
SLIDE_INTERVAL = 5


class LockScreenWindow:
    """Full-screen overlay window that simulates a lock screen."""

    def __init__(self, image_path=None, agent_key=""):
        self._root = None
        self._thread = None
        self._image_paths = []  # 支持多张图片
        self._current_index = 0
        self._agent_key = agent_key
        self._is_locked = False
        self._slide_running = False
        self._bg_label = None
        self._photo_images = []

    @property
    def is_locked(self):
        return self._is_locked

    def show(self, image_path=None):
        """Show the lock screen window in a separate thread."""
        if self._is_locked:
            return
        if image_path:
            # 支持单张或多张图片（传入列表）
            if isinstance(image_path, list):
                self._image_paths = [p for p in image_path if p and os.path.exists(p)]
            elif os.path.exists(image_path):
                self._image_paths = [image_path]
            else:
                self._image_paths = []
        self._is_locked = True
        self._current_index = 0
        self._thread = threading.Thread(target=self._create_window, daemon=True)
        self._thread.start()

    def hide(self):
        """Hide (destroy) the lock screen window."""
        self._slide_running = False
        if self._root and self._is_locked:
            try:
                self._root.after(0, self._destroy)
            except Exception:
                pass
        self._is_locked = False

    def update_image(self, image_path):
        """Update the background image (will take effect on next lock)."""
        if isinstance(image_path, list):
            self._image_paths = [p for p in image_path if p and os.path.exists(p)]
        elif os.path.exists(image_path):
            self._image_paths = [image_path]
        else:
            self._image_paths = []

    def _generate_qr_image(self, size=200):
        """Generate a QR code PIL Image for the scan-unlock URL."""
        if qrcode is None:
            logger.warning("qrcode 库未安装，无法生成二维码")
            return None
        url = QR_URL_TEMPLATE.format(agent_key=self._agent_key)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        return img

    def _create_window(self):
        """Create the fullscreen tkinter window."""
        logger.info("🔧 正在创建锁屏窗口...")
        self._root = tk.Tk()
        self._root.attributes('-fullscreen', True)
        self._root.attributes('-topmost', True)
        self._root.configure(bg='black')
        self._root.title("锁屏")

        # Remove window decorations
        self._root.overrideredirect(True)

        # Get screen dimensions
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        # Preload all images
        self._photo_images = []
        for img_path in self._image_paths:
            try:
                img = Image.open(img_path)
                img = img.resize((screen_w, screen_h), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._photo_images.append(photo)
            except Exception as e:
                logger.warning(f"加载图片失败: {img_path}, {e}")

        # Display background (single image or slideshow)
        if self._photo_images:
            # Create label for background
            self._bg_label = Label(self._root, image=self._photo_images[0])
            self._bg_label.pack(fill=tk.BOTH, expand=True)

            # Start slideshow if more than one image
            if len(self._photo_images) > 1:
                self._slide_running = True
                self._start_slideshow()
        else:
            self._show_default_lock(screen_w, screen_h)

        # Overlay QR code on top of the background
        self._overlay_qr_code(screen_w, screen_h)

        # Block keyboard shortcuts
        self._root.bind('<Alt-F4>', lambda e: 'break')
        self._root.bind('<Alt-Tab>', lambda e: 'break')
        self._root.bind('<Control-Alt-Delete>', lambda e: 'break')
        self._root.bind('<Escape>', lambda e: 'break')
        self._root.bind('<Alt_L>', lambda e: 'break')
        self._root.bind('<Alt_R>', lambda e: 'break')

        # Prevent window from being closed
        self._root.protocol("WM_DELETE_WINDOW", lambda: None)

        # Keep window on top with periodic check
        self._keep_on_top()

        self._root.mainloop()

    def _start_slideshow(self):
        """Start the image slideshow."""
        if not self._slide_running or not self._root:
            return

        try:
            self._current_index = (self._current_index + 1) % len(self._photo_images)
            self._bg_label.configure(image=self._photo_images[self._current_index])
            # Schedule next slide
            self._root.after(int(SLIDE_INTERVAL * 1000), self._start_slideshow)
        except Exception as e:
            logger.warning(f"轮播图片失败: {e}")

    def _show_default_lock(self, width, height):
        """Show default lock screen with text message."""
        canvas = tk.Canvas(self._root, width=width, height=height, bg='#1a1a2e', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # Gradient-like effect with rectangles
        for i in range(10):
            alpha = i * 0.1
            y = height * i // 10
            canvas.create_rectangle(0, y, width, y + height // 10, fill=f'#{16 + i * 3:02x}{16 + i * 2:02x}{30 + i * 5:02x}', outline='')

        # Lock icon text
        canvas.create_text(width // 2, height // 2 - 40, text="🔒", font=("", 72), fill="white")
        canvas.create_text(width // 2, height // 2 + 60, text="设备已锁定", font=("Microsoft YaHei", 36, "bold"), fill="white")
        canvas.create_text(width // 2, height // 2 + 120, text="请使用微信扫描右下角二维码解锁", font=("Microsoft YaHei", 18), fill="#aaaaaa")

    def _overlay_qr_code(self, screen_w, screen_h):
        """Place the QR code image in the bottom-right corner."""
        if not self._agent_key:
            logger.warning("未设置 agent_key，无法生成二维码")
            return

        qr_size = min(screen_w, screen_h) // 5  # ~20% of smaller dimension
        qr_size = max(qr_size, 160)  # minimum 160px
        qr_size = min(qr_size, 280)  # maximum 280px

        qr_img = self._generate_qr_image(qr_size)
        if qr_img is None:
            return

        # Convert to PhotoImage
        self._qr_photo = ImageTk.PhotoImage(qr_img)

        # Position: bottom-right with padding
        padding = 40
        x = screen_w - qr_size - padding
        y = screen_h - qr_size - padding - 30  # extra space for label

        qr_label = tk.Label(self._root, image=self._qr_photo, bd=0, bg="white")
        qr_label.place(x=x, y=y, width=qr_size, height=qr_size)

        # Text label below QR code
        text_label = tk.Label(
            self._root,
            text="微信扫码解锁",
            font=("Microsoft YaHei", 14, "bold"),
            fg="white",
            bg="#1a1a2e",
        )
        text_label.place(x=x, y=y + qr_size + 5, width=qr_size)

    def _keep_on_top(self):
        """Periodically ensure the window stays on top."""
        if self._root and self._is_locked:
            try:
                self._root.attributes('-topmost', True)
                self._root.lift()
                self._root.focus_force()
                self._root.after(1000, self._keep_on_top)
            except Exception:
                pass

    def _destroy(self):
        """Destroy the window safely."""
        try:
            self._root.destroy()
        except Exception:
            pass
        self._root = None
        self._is_locked = False
