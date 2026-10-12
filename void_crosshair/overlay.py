"""The overlay: a tiny transparent, click-through window that only paints the crosshair."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QGuiApplication, QPainter, QScreen
from PySide6.QtWidgets import QWidget

from void_crosshair import render
from void_crosshair.config import Settings


def platform() -> str:
    return QGuiApplication.platformName()


def target_rect(s: Settings, screen: QRect) -> QRect:
    """Where the overlay window goes: a square around the screen centre plus the offset."""
    half = render.extent(s)
    cx = screen.x() + screen.width() // 2 + s.offset_x
    cy = screen.y() + screen.height() // 2 + s.offset_y
    return QRect(cx - half, cy - half, half * 2, half * 2)


class Overlay(QWidget):
    def __init__(self, settings: Settings, screen: QScreen) -> None:
        super().__init__(None)
        self.settings = settings
        self.image_ok = True
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.WindowTransparentForInput
                 | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.Tool)
        if platform() == "xcb":
            # Unmanaged (override-redirect) windows sit above everything, fullscreen
            # games included, and never show in the taskbar or the window switcher.
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setWindowTitle("THE VOID CROSSHAIR overlay")
        self.place(screen)

    def place(self, screen: QScreen) -> None:
        self.target = screen
        if self.windowHandle() is not None:
            self.windowHandle().setScreen(screen)
        geo = screen.geometry()
        if platform() == "wayland":
            # Native Wayland clients cannot position themselves: cover the screen instead
            # and draw at the centre. (By default the app runs through XWayland.)
            self.setGeometry(geo)
        else:
            self.setGeometry(target_rect(self.settings, geo))
        self.update()

    def centre(self) -> QPoint:
        if platform() == "wayland":
            g = self.target.geometry()
            return QPoint(g.width() // 2 + self.settings.offset_x,
                          g.height() // 2 + self.settings.offset_y)
        return QPoint(self.width() // 2, self.height() // 2)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        c = self.centre()
        self.image_ok = render.paint(p, self.settings, c.x(), c.y())
        p.end()
