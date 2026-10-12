"""Draw a crosshair with QPainter: vector styles, or any PNG / SVG image."""

from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPixmap,
    QPolygonF,
    QTransform,
)
from PySide6.QtSvg import QSvgRenderer

from void_crosshair.config import Settings

IMAGE_TYPES = ("png", "svg", "webp", "jpg", "jpeg", "bmp", "gif")


def shape(s: Settings) -> QPainterPath:
    """The crosshair's filled outline, centred on (0, 0), before outline/opacity."""
    r = s.size / 2
    t = s.thickness
    g = min(s.gap, max(r - 1, 0))
    p = QPainterPath()
    p.setFillRule(Qt.FillRule.WindingFill)

    def arms(top: bool = True) -> None:
        length = r - g
        if length <= 0:
            return
        p.addRect(QRectF(g, -t / 2, length, t))
        p.addRect(QRectF(-r, -t / 2, length, t))
        p.addRect(QRectF(-t / 2, g, t, length))
        if top:
            p.addRect(QRectF(-t / 2, -r, t, length))

    def dot(radius: float) -> None:
        if radius > 0:
            p.addEllipse(QPointF(0, 0), radius, radius)

    def ring() -> None:
        circle = QPainterPath()
        circle.addEllipse(QPointF(0, 0), r - t / 2, r - t / 2)
        st = QPainterPathStroker()
        st.setWidth(t)
        p.addPath(st.createStroke(circle))

    def stroke(points: list[tuple[float, float]], closed: bool = False) -> None:
        line = QPainterPath()
        line.addPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
        if closed:
            line.closeSubpath()
        st = QPainterPathStroker()
        st.setWidth(t)
        st.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        st.setCapStyle(Qt.PenCapStyle.SquareCap if closed else Qt.PenCapStyle.FlatCap)
        p.addPath(st.createStroke(line))

    style = s.style
    if style in ("cross", "x"):
        arms()
    elif style == "cross_dot":
        arms()
        dot(s.dot or t / 2)
    elif style == "t":
        arms(top=False)
        if s.dot:
            dot(s.dot)
    elif style == "dot":
        dot(max(s.dot, 1))
    elif style == "circle":
        ring()
    elif style == "circle_dot":
        ring()
        dot(s.dot or max(t, 1))
    elif style == "circle_cross":
        ring()
        arms()
        if s.dot:
            dot(s.dot)
    elif style == "chevron":
        stroke([(-r, r * 0.65), (0, 0), (r, r * 0.65)])
    elif style == "square":
        h = r - t / 2
        stroke([(-h, -h), (h, -h), (h, h), (-h, h)], closed=True)
        if s.dot:
            dot(s.dot)
    elif style == "triangle":
        stroke([(0, -r), (r * 0.87, r * 0.5), (-r * 0.87, r * 0.5)], closed=True)
        if s.dot:
            dot(s.dot)
    p = p.simplified()
    angle = s.rotation + (45 if style == "x" else 0)
    if angle:
        p = QTransform().rotate(angle).map(p)
    return p


def extent(s: Settings) -> int:
    """Half the side of a square that holds the crosshair at any rotation."""
    pad = (s.outline_width if s.outline else 0) + 2
    return math.ceil(s.size / 2 * math.sqrt(2)) + pad


@lru_cache(maxsize=32)
def _image(path: str, size: int) -> QImage | None:
    if path.lower().endswith(".svg"):
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            return None
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        with_painter = QPainter(img)
        with_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = renderer.defaultSize().scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio)
        renderer.render(with_painter, QRectF((size - box.width()) / 2,
                                             (size - box.height()) / 2,
                                             box.width(), box.height()))
        with_painter.end()
        return img
    img = QImage(path)
    if img.isNull():
        return None
    return img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)


def _tinted(img: QImage, color: str) -> QImage:
    out = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return out


def paint(p: QPainter, s: Settings, cx: float, cy: float) -> bool:
    """Draw the crosshair centred on (cx, cy). Returns False if an image failed to load."""
    p.save()
    p.setOpacity(s.opacity)
    # Odd line widths are centred on a pixel, so shift by half a pixel to keep them sharp.
    half = 0.5 if s.thickness % 2 else 0.0
    p.translate(cx + half, cy + half)
    ok = True
    if s.style == "image":
        img = _image(s.image, max(s.size, 4)) if s.image else None
        if img is None:
            ok = False
        else:
            if s.tint_image:
                img = _tinted(img, s.color)
            p.rotate(s.rotation)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QPointF(-img.width() / 2 - half, -img.height() / 2 - half), img)
    else:
        path = shape(s)
        curved = s.style not in ("cross", "t", "square") or s.rotation % 90 != 0
        p.setRenderHint(QPainter.RenderHint.Antialiasing, curved)
        if s.outline and s.outline_width > 0:
            pen = QPen(QColor(s.outline_color), s.outline_width * 2)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(s.color))
        p.drawPath(path)
    p.restore()
    return ok


def pixmap(s: Settings, side: int, background: QColor | None = None) -> QPixmap:
    """A square picture of the crosshair (thumbnails, previews, icons)."""
    pm = QPixmap(side, side)
    pm.fill(background or Qt.GlobalColor.transparent)
    p = QPainter(pm)
    paint(p, s, side / 2, side / 2)
    p.end()
    return pm
