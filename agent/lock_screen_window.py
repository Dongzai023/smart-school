"""Lock screen full-screen overlay window.

Uses tkinter to create a frameless, topmost, fullscreen window
that displays the lock screen background image.
This window intercepts Alt+F4 and other escape attempts.
"""

import os
import threading
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import logging

logger = logging.getLogger("agent.lock_window")


class LockScreenWindow:
    """Full-screen overlay window that simulates a lock screen."""

    def __init__(self, image_path=None):
        self._root = None
        self._thread = None
        self._image_path = image_path
        self._is_locked = False

    @property
    def is_locked(self):
        return self._is_locked

    def show(self, image_path=None):
        """Show the lock screen window in a separate thread."""
        if self._is_locked:
            return
        if image_path:
            self._image_path = image_path
        self._is_locked = True
        self._thread = threading.Thread(target=self._create_window, daemon=True)
        self._thread.start()

    def hide(self):
        """Hide (destroy) the lock screen window."""
        if self._root and self._is_locked:
            try:
                self._root.after(0, self._destroy)
            except Exception:
                pass
        self._is_locked = False

    def update_image(self, image_path):
        """Update the background image (will take effect on next lock)."""
        self._image_path = image_path

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

        # Display background image
        if self._image_path and os.path.exists(self._image_path):
            try:
                img = Image.open(self._image_path)
                img = img.resize((screen_w, screen_h), Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                label = Label(self._root, image=self._photo)
                label.pack(fill=tk.BOTH, expand=True)
            except Exception:
                # Fallback to solid color
                self._show_default_lock(screen_w, screen_h)
        else:
            self._show_default_lock(screen_w, screen_h)

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
        canvas.create_text(width // 2, height // 2 + 120, text="请联系管理员解锁", font=("Microsoft YaHei", 18), fill="#aaaaaa")

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
