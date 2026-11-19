
import sys
import os
import time
import ctypes
import ctypes.wintypes
import threading

# ============================================================
# WINDOWS DPI AWARENESS
# ============================================================

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.SetProcessDpiAwarenessContext(
    ctypes.c_void_p(-4)
)

# ============================================================
# SETTINGS FROM BAT
# ============================================================

BASE_SIZE = float(os.getenv("BASE_SIZE", "1.5"))
CLICK_SIZE = float(os.getenv("CLICK_SIZE", "0.75"))

SHRINK_TIME = float(os.getenv("SHRINK_TIME", "0.5"))
GROW_TIME = float(os.getenv("GROW_TIME", "0.1"))

TIP_X = int(os.getenv("TIP_X", "15"))
TIP_Y = int(os.getenv("TIP_Y", "15"))

UPDATE_MS = int(os.getenv("UPDATE_MS", "0"))

SMOOTHSTEP = int(os.getenv("SMOOTHSTEP", "0"))
HIDE_NATIVE_CURSOR = int(os.getenv("HIDE_NATIVE_CURSOR", "1"))

# ============================================================
# WINDOWS API
# ============================================================

user32.GetCursorPos.argtypes = [
    ctypes.POINTER(ctypes.wintypes.POINT)
]

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

user32.SetWindowPos.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint
]

user32.SetWindowPos.restype = ctypes.c_bool

user32.ShowCursor.argtypes = [ctypes.wintypes.BOOL]
user32.ShowCursor.restype = ctypes.c_int

HWND_TOPMOST = ctypes.wintypes.HWND(-1)

SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200

# ============================================================
# QT
# ============================================================

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF

# ============================================================
# SHARED STATE
# ============================================================

running = True

mouse_x = 0
mouse_y = 0

left_pressed = False
right_pressed = False

state_lock = threading.Lock()

# ============================================================
# NATIVE CURSOR VISIBILITY
# ============================================================

cursor_hidden = False


def hide_native_cursor():

    global cursor_hidden

    if HIDE_NATIVE_CURSOR:
        # ShowCursor uses a counter. Keep decrementing until hidden.
        for _ in range(20):
            if user32.ShowCursor(False) < 0:
                break

        cursor_hidden = True


def restore_native_cursor():

    global cursor_hidden

    if cursor_hidden:
        # Restore the display counter.
        for _ in range(20):
            if user32.ShowCursor(True) >= 0:
                break

        cursor_hidden = False


# ============================================================
# MOUSE TRACKING THREAD
# ============================================================

def mouse_tracking_thread(hwnd):

    global mouse_x, mouse_y
    global left_pressed, right_pressed

    pt = ctypes.wintypes.POINT()

    flags = SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER

    while running:

        user32.GetCursorPos(ctypes.byref(pt))

        x = pt.x
        y = pt.y

        left = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        right = bool(user32.GetAsyncKeyState(0x02) & 0x8000)

        with state_lock:
            mouse_x = x
            mouse_y = y
            left_pressed = left
            right_pressed = right

        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            x - TIP_X,
            y - TIP_Y,
            0,
            0,
            flags
        )

        if UPDATE_MS > 0:
            time.sleep(UPDATE_MS / 1000.0)
        else:
            time.sleep(0)

# ============================================================
# OVERLAY
# ============================================================

class MouseOverlay(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.resize(160, 160)
        self.show()

        self.hwnd = int(self.winId())

        self.scale = BASE_SIZE
        self.phase = None
        self.start_time = 0

        self.last_left = False
        self.last_right = False

        # Native tracking
        self.tracker = threading.Thread(
            target=mouse_tracking_thread,
            args=(self.hwnd,),
            daemon=True
        )

        self.tracker.start()

        # Animation timer only
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(8)

        hide_native_cursor()

    # ========================================================
    # INTERPOLATION
    # ========================================================

    def interpolate(self, t):

        t = max(0.0, min(1.0, t))

        if SMOOTHSTEP:
            return t * t * (3.0 - 2.0 * t)

        # Ordinary linear interpolation
        return t

    # ========================================================
    # ANIMATION
    # ========================================================

    def update_animation(self):

        now = time.perf_counter()

        with state_lock:
            left = left_pressed
            right = right_pressed

        if (left and not self.last_left) or \
           (right and not self.last_right):

            self.phase = "shrink"
            self.start_time = now

        self.last_left = left
        self.last_right = right

        if self.phase == "shrink":

            t = min((now - self.start_time) / SHRINK_TIME, 1.0)
            t = self.interpolate(t)

            self.scale = BASE_SIZE + (CLICK_SIZE - BASE_SIZE) * t

            if t >= 1:
                self.phase = "grow"
                self.start_time = now

        elif self.phase == "grow":

            t = min((now - self.start_time) / GROW_TIME, 1.0)
            t = self.interpolate(t)

            self.scale = CLICK_SIZE + (BASE_SIZE - CLICK_SIZE) * t

            if t >= 1:
                self.scale = BASE_SIZE
                self.phase = None

        self.update()

    # ========================================================
    # DRAW
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        points = [
            (0, 0),
            (0, 36),
            (9, 27),
            (16, 42),
            (22, 39),
            (15, 24),
            (29, 24)
        ]

        polygon = QPolygonF([
            QPointF(
                TIP_X + x * self.scale,
                TIP_Y + y * self.scale
            )
            for x, y in points
        ])

        painter.setPen(QPen(QColor("black"), 3))
        painter.setBrush(QBrush(QColor("white")))
        painter.drawPolygon(polygon)

        painter.end()

    # ========================================================
    # EXIT
    # ========================================================

    def closeEvent(self, event):

        global running

        running = False

        if self.tracker.is_alive():
            self.tracker.join(timeout=0.5)

        restore_native_cursor()

        event.accept()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    overlay = MouseOverlay()

    app.aboutToQuit.connect(restore_native_cursor)

    try:
        sys.exit(app.exec())

    finally:
        running = False
        restore_native_cursor()
