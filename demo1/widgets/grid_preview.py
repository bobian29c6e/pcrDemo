from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget


class GridPreviewWidget(QWidget):
    """
    Fine-grid background with a movable inner rectangle (viewport).
    Supports mouse drag, easing pan updates, and nudge(dx, dy).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 150)
        # background fine grid config
        self._pad = 6  # padding to frame
        self._grid_step_min = 4
        self._grid_color_minor = QColor(180, 195, 205, 38)
        self._grid_color_major = QColor(190, 210, 220, 72)

        # pan state (normalized [-1, 1]) and UI behavior
        self._panx = 0.0
        self._pany = 0.0
        self._ease_alpha = 0.15  # exponential smoothing factor
        self._sensitivity = 0.8
        self._inner_ratio = 0.3  # inner box size relative to grid

        self._dragging = False
        self._last_grid_rect = QRect()
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(320, 220)

    def setPan(self, x: float, y: float):
        # sensitivity and clamp
        tx = max(-1.0, min(1.0, float(x) * self._sensitivity))
        ty = max(-1.0, min(1.0, float(y) * self._sensitivity))
        a = self._ease_alpha
        self._panx = (1 - a) * self._panx + a * tx
        self._pany = (1 - a) * self._pany + a * ty
        self.update()

    # --- painting ---
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        outer = self.rect().adjusted(2, 2, -2, -2)

        # card background & outer frame
        p.fillRect(outer, QColor('#1e1f22'))
        p.setPen(QPen(QColor(58, 63, 69, 180), 1))
        p.drawRoundedRect(outer, 6, 6)

        # grid rectangle
        avail_w = max(0, outer.width() - 2 * self._pad)
        avail_h = max(0, outer.height() - 2 * self._pad)
        grid_w = avail_w
        grid_h = avail_h
        gx = int(outer.left() + (outer.width() - grid_w) / 2)
        gy = int(outer.top() + (outer.height() - grid_h) / 2)
        grid_rect = QRect(gx, gy, int(grid_w), int(grid_h))
        self._last_grid_rect = grid_rect

        # fine grid lines (minor/major)
        step = max(self._grid_step_min, max(4, min(grid_rect.width(), grid_rect.height()) // 40))
        # vertical
        i = 0
        x = grid_rect.left()
        while x <= grid_rect.right():
            is_major = (i % 5 == 0)
            pen = QPen(self._grid_color_major if is_major else self._grid_color_minor)
            pen.setWidth(1)
            p.setPen(pen)
            p.drawLine(x, grid_rect.top(), x, grid_rect.bottom())
            x += step
            i += 1
        # horizontal
        i = 0
        y = grid_rect.top()
        while y <= grid_rect.bottom():
            is_major = (i % 5 == 0)
            pen = QPen(self._grid_color_major if is_major else self._grid_color_minor)
            pen.setWidth(1)
            p.setPen(pen)
            p.drawLine(grid_rect.left(), y, grid_rect.right(), y)
            y += step
            i += 1

        # grid frame
        p.setPen(QPen(QColor(125, 140, 150, 180), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(grid_rect, 4, 4)

        # inner viewport rectangle
        inner_w = int(grid_rect.width() * self._inner_ratio)
        inner_h = int(grid_rect.height() * self._inner_ratio)
        max_dx = (grid_rect.width() - inner_w) // 2
        max_dy = (grid_rect.height() - inner_h) // 2
        cx = grid_rect.center().x() + int(self._panx * max_dx)
        cy = grid_rect.center().y() + int(self._pany * max_dy)
        inner_rect = QRect(cx - inner_w // 2, cy - inner_h // 2, inner_w, inner_h)

        glow = QColor(46, 196, 182, 75)
        p.setBrush(glow)
        p.setPen(QPen(QColor(46, 196, 182), 2))
        p.drawRoundedRect(inner_rect, 6, 6)
        p.fillRect(inner_rect.adjusted(2, 2, -2, -2), QColor(46, 196, 182, 18))
        p.end()

    # --- mouse interactions ---
    def enterEvent(self, e):
        self.setCursor(Qt.OpenHandCursor)
        return super().enterEvent(e)

    def leaveEvent(self, e):
        self.unsetCursor()
        return super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)
            self._update_pan_from_point(e.position())
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging and (e.buttons() & Qt.LeftButton):
            self._update_pan_from_point(e.position())
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._dragging and e.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.OpenHandCursor)
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    def _update_pan_from_point(self, posf):
        grid = self._last_grid_rect if not self._last_grid_rect.isNull() else self.rect()
        gx, gy, gw, gh = grid.x(), grid.y(), grid.width(), grid.height()
        if gw <= 0 or gh <= 0:
            return
        inner_w = int(gw * self._inner_ratio)
        inner_h = int(gh * self._inner_ratio)
        max_dx = (gw - inner_w) // 2
        max_dy = (gh - inner_h) // 2
        px = int(min(max(posf.x(), gx), gx + gw))
        py = int(min(max(posf.y(), gy), gy + gh))
        cx = px
        cy = py
        panx = 0.0 if max_dx == 0 else (cx - (gx + gw // 2)) / max_dx
        pany = 0.0 if max_dy == 0 else (cy - (gy + gh // 2)) / max_dy
        self.setPan(panx, pany)

    def nudge(self, dx: float, dy: float):
        self._panx = max(-1.0, min(1.0, self._panx + dx))
        self._pany = max(-1.0, min(1.0, self._pany + dy))
        self.update()
