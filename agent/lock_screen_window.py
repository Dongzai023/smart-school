"""Lock screen full-screen overlay window.

Uses tkinter to create a frameless, topmost, fullscreen window
that displays the lock screen background image.
This window intercepts Alt+F4 and other escape attempts.
Refactored for thread safety using a single persistent UI thread.
"""

import os
import threading
import queue
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import logging

logger = logging.getLogger("agent.lock_window")


class LockScreenWindow:
    """Full-screen overlay window that simulates a lock screen."""

    def __init__(self, image_path=None):
        self._image_path = image_path
        self._is_locked = False
        self._queue = queue.Queue()
        
        # Internal UI state
        self._root = None
        self._photo = None
        self._label = None
        
        # Start persistent UI thread
        self._thread = threading.Thread(target=self._ui_thread, daemon=True)
        self._thread.start()

    @property
    def is_locked(self):
        return self._is_locked

    def show(self, image_path=None):
        """Request the lock screen to be shown."""
        if image_path:
            self._image_path = image_path
        self._queue.put(('SHOW', self._image_path))
        self._is_locked = True

    def hide(self):
        """Request the lock screen to be hidden."""
        self._queue.put(('HIDE', None))
        self._is_locked = False

    def update_image(self, image_path):
        """Update the background image."""
        self._image_path = image_path
        # If currently locked, refresh immediately
        if self._is_locked:
            self._queue.put(('SHOW', self._image_path))

    def _ui_thread(self):
        """Main UI thread managing the Tkinter lifecycle."""
        try:
            self._root = tk.Tk()
            self._root.withdraw()  # Start hidden
            
            # Configure window
            self._root.attributes('-fullscreen', True)
            self._root.attributes('-topmost', True)
            self._root.configure(bg='black')
            self._root.overrideredirect(True)
            self._root.title("锁屏")
            
            # Block keyboard shortcuts
            self._root.bind('<Alt-F4>', lambda e: 'break')
            self._root.bind('<Alt-Tab>', lambda e: 'break')
            self._root.bind('<Control-Alt-Delete>', lambda e: 'break')
            self._root.bind('<Escape>', lambda e: 'break')
            self._root.bind('<Alt_L>', lambda e: 'break')
            self._root.bind('<Alt_R>', lambda e: 'break')
            
            # Prevent window from being closed
            self._root.protocol("WM_DELETE_WINDOW", lambda: None)
            
            # Start queue checking
            self._check_queue_loop()
            
            # Start keep-on-top loop
            self._keep_on_top_loop()
            
            self._root.mainloop()
        except Exception as e:
            logger.error(f"UI Thread error: {e}")

    def _check_queue_loop(self):
        """Periodically check the command queue."""
        try:
            while True:
                cmd, data = self._queue.get_nowait()
                if cmd == 'SHOW':
                    self._show_window(data)
                elif cmd == 'HIDE':
                    self._hide_window()
        except queue.Empty:
            pass
        
        if self._root:
            self._root.after(100, self._check_queue_loop)

    def _keep_on_top_loop(self):
        """Ensure the window stays on top if locked."""
        if self._root and self._is_locked:
            try:
                self._root.attributes('-topmost', True)
                self._root.lift()
                self._root.focus_force()
            except Exception:
                pass
        
        if self._root:
            self._root.after(1000, self._keep_on_top_loop)

    def _show_window(self, image_path):
        """Actually show and update the window content."""
        logger.info("🔧 正在锁定屏幕...")
        
        # Clear previous content
        for widget in self._root.winfo_children():
            widget.destroy()
            
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img = img.resize((screen_w, screen_h), Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                self._label = Label(self._root, image=self._photo, bg='black')
                self._label.pack(fill=tk.BOTH, expand=True)
            except Exception as e:
                logger.warning(f"加载图片失败: {e}，将使用默认背景")
                self._draw_default_background(screen_w, screen_h)
        else:
            self._draw_default_background(screen_w, screen_h)

        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def _hide_window(self):
        """Actually hide the window."""
        logger.info("🔓 正在解锁屏幕...")
        if self._root:
            self._root.withdraw()

    def _draw_default_background(self, width, height):
        """Draw default background with text message."""
        canvas = tk.Canvas(self._root, width=width, height=height, bg='#1a1a2e', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        for i in range(10):
            y = height * i // 10
            canvas.create_rectangle(0, y, width, y + height // 10, 
                                 fill=f'#{16 + i * 3:02x}{16 + i * 2:02x}{30 + i * 5:02x}', 
                                 outline='')

        canvas.create_text(width // 2, height // 2 - 40, text="🔒", font=("", 72), fill="white")
        canvas.create_text(width // 2, height // 2 + 60, text="设备已锁定", 
                          font=("Microsoft YaHei", 36, "bold"), fill="white")
        canvas.create_text(width // 2, height // 2 + 120, text="请联系管理员解锁", 
                          font=("Microsoft YaHei", 18), fill="#aaaaaa")
