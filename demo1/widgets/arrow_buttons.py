from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor, QIcon, QPolygon
from PySide6.QtWidgets import QToolButton, QGraphicsDropShadowEffect


def make_arrow_btn(parent, direction: str, w: int, h: int, scale_fn=lambda x: x) -> QToolButton:
    """
    Create a minimalist ghost-style arrow button with a drawn triangular icon.
    - direction: 'Up' | 'Down' | 'Left' | 'Right'
    - w, h: logical size before applying scale_fn
    - scale_fn: function to scale pixel values (e.g., parent.s)
    """
    btn = QToolButton(parent)
    btn.setAutoRaise(False)
    btn.setObjectName(f"nudge{direction}")
    btn.setFixedSize(scale_fn(w), scale_fn(h))

    # Icon size ratio and triangle thickness tuned for clarity
    iw, ih = max(8, int(w * 0.50)), max(8, int(h * 0.50))
    pm = QPixmap(scale_fn(iw), scale_fn(ih))
    pm.fill(Qt.transparent)

    qp = QPainter(pm)
    qp.setRenderHint(QPainter.Antialiasing)
    qp.setPen(Qt.NoPen)
    qp.setBrush(QColor('#cfd6de'))

    margin = scale_fn(3)
    w2, h2 = pm.width(), pm.height()
    if direction == 'Up':
        base_y = h2 - margin
        apex_y = margin
        half_w = int(w2 * 0.32)
        cx = w2 // 2
        poly = QPolygon([QPoint(cx, apex_y), QPoint(cx - half_w, base_y), QPoint(cx + half_w, base_y)])
    elif direction == 'Down':
        base_y = margin
        tip_y = h2 - margin
        half_w = int(w2 * 0.32)
        cx = w2 // 2
        poly = QPolygon([QPoint(cx - half_w, base_y), QPoint(cx + half_w, base_y), QPoint(cx, tip_y)])
    elif direction == 'Left':
        base_x = w2 - margin
        tip_x = margin
        half_h = int(h2 * 0.32)
        cy = h2 // 2
        poly = QPolygon([QPoint(tip_x, cy), QPoint(base_x, cy - half_h), QPoint(base_x, cy + half_h)])
    else:  # Right
        base_x = margin
        tip_x = w2 - margin
        half_h = int(h2 * 0.32)
        cy = h2 // 2
        poly = QPolygon([QPoint(base_x, cy - half_h), QPoint(tip_x, cy), QPoint(base_x, cy + half_h)])

    qp.drawPolygon(poly)
    qp.end()

    btn.setIcon(QIcon(pm))
    btn.setIconSize(pm.size())

    eff = QGraphicsDropShadowEffect(parent)
    eff.setBlurRadius(10)
    eff.setXOffset(0)
    eff.setYOffset(2)
    eff.setColor(QColor(0, 0, 0, 120))
    btn.setGraphicsEffect(eff)
    return btn
