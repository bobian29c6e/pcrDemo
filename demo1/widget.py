# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QSlider,
    QSpinBox,
    QCheckBox,
    QTabWidget,
    QPushButton,
    QToolButton,
    QLineEdit,
    QFileDialog,
    QButtonGroup,
    QFrame,
    QScrollArea,
    QGridLayout,
    QSpacerItem,
)
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont, QIcon
from PySide6.QtCore import Qt, QPoint, QRect, QSize, Signal
from PySide6.QtWidgets import QSplitter, QSizePolicy, QGraphicsDropShadowEffect
from PySide6.QtWidgets import QWidget as _QW
import numpy as np
import cv2
import os

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_Widget
from camera_worker import CameraWorker
from widgets.arrow_buttons import make_arrow_btn
from widgets.grid_preview import GridPreviewWidget
from tabs.temp_tab import build_temp_tab
from tabs.pump_tab import build_pump_tab
from tabs.misc_tab import build_misc_tab
from tabs.video_tab import build_video_tab

class JoystickWidget(_QW):
    """A lightweight placeholder joystick. Emits no signals yet; visual only."""
    # Signal must be a class attribute in PySide
    moveVector = Signal(float, float)  # normalized dx, dy in [-1, 1]
    def __init__(self, parent=None):
        super().__init__(parent)
        # Fixed square to avoid distortion
        self.setFixedSize(140, 140)
        self._pos = QPoint(0, 0)
        self._radius_factor = 0.35
    def sizeHint(self):
        return QSize(140, 140)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        # outer circle
        p.setPen(QPen(QColor('#888'), 2))
        p.setBrush(QColor('#333'))
        radius = min(rect.width(), rect.height())
        circle = QRect(rect.x(), rect.y(), radius, radius)
        p.drawEllipse(circle)
        # knob
        p.setBrush(QColor('#bbb'))
        p.setPen(QPen(QColor('#555'), 1))
        k = int(radius * 0.18)
        cx = circle.center().x() + self._pos.x()
        cy = circle.center().y() + self._pos.y()
        p.drawEllipse(QPoint(cx, cy), k, k)

    def mouseMoveEvent(self, e):
        self._update_pos(e.pos())

    def mousePressEvent(self, e):
        self._update_pos(e.pos())

    def mouseReleaseEvent(self, e):
        self._pos = QPoint(0, 0)
        self.update()
        # keep last pan; do not emit recenter

    def _update_pos(self, pos):
        c = self.rect().center()
        v = QPoint(pos.x() - c.x(), pos.y() - c.y())
        # clamp to radius
        r = min(self.rect().width(), self.rect().height()) * self._radius_factor
        if v.manhattanLength() > 0:
            # simple clamp
            vx, vy = v.x(), v.y()
            mag2 = max(1.0, (vx*vx + vy*vy) ** 0.5)
            if mag2 > r:
                scale = r / mag2
                v = QPoint(int(vx * scale), int(vy * scale))
        self._pos = v
        self.update()
        # emit normalized vector
        if r > 0:
            self.moveVector.emit(v.x() / r, v.y() / r)

class GridPreviewWidget(_QW):
    """Paints a responsive grid preview that keeps aspect and redraws on resize."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 150)
        # background fine grid config
        self._pad = 6  # a bit more padding for frame
        self._grid_step_min = 4  # px, min spacing for fine grid
        self._grid_color_minor = QColor(180, 195, 205, 38)
        self._grid_color_major = QColor(190, 210, 220, 72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # small viewport (movable) pan state, normalized [-1,1]
        self._panx = 0.0
        self._pany = 0.0
        # easing (exponential smoothing) and sensitivity
        self._ease_alpha = 0.15  # 0..1, larger = faster follow
        self._sensitivity = 0.8  # <1 means less sensitive
        # inner box size ratio relative to grid size
        self._inner_ratio = 0.3
        self._dragging = False
        self._last_grid_rect = QRect()
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(320, 220)

    def setPan(self, x: float, y: float):
        # apply sensitivity and clamp to [-1,1]
        tx = max(-1.0, min(1.0, float(x) * self._sensitivity))
        ty = max(-1.0, min(1.0, float(y) * self._sensitivity))
        # exponential smoothing
        a = self._ease_alpha
        self._panx = (1 - a) * self._panx + a * tx
        self._pany = (1 - a) * self._pany + a * ty
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        outer = self.rect().adjusted(2, 2, -2, -2)
        # card background
        p.fillRect(outer, QColor('#1e1f22'))
        # rounded border (softer)
        p.setPen(QPen(QColor(58, 63, 69, 180), 1))
        p.drawRoundedRect(outer, 6, 6)

        # compute grid rect with padding
        avail_w = max(0, outer.width() - 2*self._pad)
        avail_h = max(0, outer.height() - 2*self._pad)
        grid_w = avail_w
        grid_h = avail_h
        gx = int(outer.left() + (outer.width() - grid_w) / 2)
        gy = int(outer.top() + (outer.height() - grid_h) / 2)
        grid_rect = QRect(gx, gy, int(grid_w), int(grid_h))
        self._last_grid_rect = grid_rect

        # draw thin background grid lines
        step = max(self._grid_step_min, max(4, min(grid_rect.width(), grid_rect.height()) // 40))
        # draw minor and major lines (every 5th is major)
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

        # draw movable inner viewport (small box inside big box), controlled by pan
        inner_w = int(grid_rect.width() * self._inner_ratio)
        inner_h = int(grid_rect.height() * self._inner_ratio)
        # center move range is limited so inner stays fully inside
        max_dx = (grid_rect.width() - inner_w) // 2
        max_dy = (grid_rect.height() - inner_h) // 2
        cx = grid_rect.center().x() + int(self._panx * max_dx)
        cy = grid_rect.center().y() + int(self._pany * max_dy)
        inner_rect = QRect(cx - inner_w // 2, cy - inner_h // 2, inner_w, inner_h)

        # inner box: subtle glow + translucent fill
        glow = QColor(46, 196, 182, 75)
        p.setBrush(glow)
        p.setPen(QPen(QColor(46, 196, 182), 2))
        p.drawRoundedRect(inner_rect, 6, 6)
        p.fillRect(inner_rect.adjusted(2,2,-2,-2), QColor(46, 196, 182, 18))

        # no corner handle for a cleaner look

        # optional center mark: small crosshair
        # remove center crosshair for a cleaner look
        p.end()

    def enterEvent(self, e):
        self.setCursor(Qt.OpenHandCursor)
        return super().enterEvent(e)

    def leaveEvent(self, e):
        self.unsetCursor()
        return super().leaveEvent(e)

    # ---- Mouse drag to move inner box ----
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
        # Ensure we have the latest grid rect
        grid = self._last_grid_rect if not self._last_grid_rect.isNull() else self.rect()
        gx, gy, gw, gh = grid.x(), grid.y(), grid.width(), grid.height()
        if gw <= 0 or gh <= 0:
            return
        inner_w = int(gw * self._inner_ratio)
        inner_h = int(gh * self._inner_ratio)
        max_dx = (gw - inner_w) // 2
        max_dy = (gh - inner_h) // 2
        # Clamp point inside grid
        px = int(min(max(posf.x(), gx), gx + gw))
        py = int(min(max(posf.y(), gy), gy + gh))
        # Desired center
        cx = px
        cy = py
        # Map to normalized [-1,1]
        panx = 0.0 if max_dx == 0 else (cx - (gx + gw // 2)) / max_dx
        pany = 0.0 if max_dy == 0 else (cy - (gy + gh // 2)) / max_dy
        self.setPan(panx, pany)

    # ---- Arrow nudge API ----
    def nudge(self, dx: float, dy: float):
        self._panx = max(-1.0, min(1.0, self._panx + dx))
        self._pany = max(-1.0, min(1.0, self._pany + dy))
        self.update()

class Widget(QWidget):
    def s(self, v: int) -> int:
        return int(round(v * self._ui_scale))

    # Reusable card factory for tabs
    def _make_card(self, title: str, icon_text: str):
        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setObjectName("card")
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 8)
        v.setSpacing(4)
        header_w = QWidget(self)
        header_w.setObjectName("cardHeader")
        header_w.setMinimumHeight(self.s(28))
        header = QHBoxLayout(header_w)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        icon_lbl = QLabel(icon_text)
        icon_lbl.setObjectName("cardIcon")
        icon_lbl.setFixedSize(self.s(26), self.s(26))
        icon_lbl.setContentsMargins(0, self.s(1), 0, self.s(1))
        icon_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        f = QFont()
        f.setBold(True)
        title_lbl.setFont(f)
        title_lbl.setMinimumHeight(self.s(22))
        header.addWidget(icon_lbl)
        header.addWidget(title_lbl)
        header.addStretch(1)
        v.addWidget(header_w)
        return frame, v

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        
        # State
        self.worker = None
        self.streaming = False
        self._ui_scale = 1.2  # global UI scaling for controls
        self._right_target_width = int(560 * self._ui_scale)  # desired right panel width when maximized

        # Video display label
        self.image_label = QLabel(self)
        self.image_label.setText("No Video")
        self.image_label.setStyleSheet("background-color: #101214; color: #9aa1a9; border: 1px solid #2b2f33; border-radius: 8px;")
        self.image_label.setMinimumSize(self.s(320), self.s(240))
        # Preserve aspect ratio on resize (we draw scaled pixmap in resizeEvent)
        self.image_label.setScaledContents(False)
        self._last_qimage = None

        # Controls for exposure/gain/gamma and display enhancement
        self.exposure_auto_cb = QComboBox(self)
        self.exposure_auto_cb.addItems(["Off", "Once", "Continuous"])  # default will be set later
        self.exposure_slider = QSlider(self)
        self.exposure_slider.setOrientation(Qt.Horizontal)
        self.exposure_slider.setRange(100, 30000)  # microseconds (generic UI range)
        self.exposure_spin = QSpinBox(self)
        self.exposure_spin.setRange(100, 30000)
        self.exposure_spin.setSuffix(" us")

        self.gain_auto_cb = QComboBox(self)
        self.gain_auto_cb.addItems(["Off", "Continuous"])  # default later
        self.gain_slider = QSlider(self)
        self.gain_slider.setOrientation(Qt.Horizontal)
        self.gain_slider.setRange(0, 120)  # represent 0.0 - 12.0 dB in 0.1 steps
        self.gain_spin = QSpinBox(self)
        self.gain_spin.setRange(0, 120)
        self.gain_spin.setSuffix(" (x0.1 dB)")

        self.gamma_chk = QCheckBox("Gamma")
        self.enhance_chk = QCheckBox("Enhance Contrast")
        self.enhance_chk.setChecked(True)
        self.enhance_contrast = True

        # Wire local UI state (spin <-> slider)
        self.exposure_slider.valueChanged.connect(self.exposure_spin.setValue)
        self.exposure_spin.valueChanged.connect(self.exposure_slider.setValue)
        self.gain_slider.valueChanged.connect(self.gain_spin.setValue)
        self.gain_spin.valueChanged.connect(self.gain_slider.setValue)

        # Layouts: left/right via splitter to control resizing ratios
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setHandleWidth(6)
        self.splitter.setChildrenCollapsible(False)
        main_layout.addWidget(self.splitter)

        # Left: video container
        left_container = QWidget(self)
        left_box = QVBoxLayout(left_container)
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(8)
        left_box.addWidget(self.image_label, 1)
        self.splitter.addWidget(left_container)

        # Right: tabs container (fixed width)
        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.tabs = QTabWidget(right_container)
        self.tabs.setDocumentMode(True)
        # Tabs style
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; }"
            "QTabBar::tab { background: #2a2d31; color: #cdd3da; padding: 7px 14px; border: 1px solid #3a3f45; border-bottom: 0; }"
            "QTabBar::tab:selected { background: #343a40; }"
            "QTabBar::tab:!selected { margin-top: 2px; }"
        )
        right_layout.addWidget(self.tabs, 1)
        right_container.setMinimumWidth(self.s(520))
        right_container.setMaximumWidth(self.s(760))
        right_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.splitter.addWidget(right_container)
        self.splitter.setStretchFactor(0, 1)  # left expands
        self.splitter.setStretchFactor(1, 0)  # right fixed

        # Tab 1: 画面控制 (built via external builder)
        tab_video_ctrl, video_refs = build_video_tab(self, self.s, self._make_card)
        # Wire references expected elsewhere in this class
        self.first_row_widget = video_refs.get("first_row_widget")
        self.grid_label = video_refs.get("grid")
        self.obj_group = video_refs.get("obj_group")
        self.obj_buttons = video_refs.get("obj_buttons", [])
        self.channel_group = video_refs.get("channel_group")
        self.channel_buttons = video_refs.get("channel_buttons", [])

        # Tab 1 UI content is provided by build_video_tab(); subsections removed from here

        # Put content inside a scroll area to avoid stretching when window is short
        scroll1 = QScrollArea(self)
        scroll1.setWidget(tab_video_ctrl)
        scroll1.setWidgetResizable(True)
        scroll1.setFrameShape(QFrame.NoFrame)
        scroll1.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll1.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tabs.addTab(scroll1, "画面控制")

        # Tab 2: 温度控制
        tab_temp = build_temp_tab(self)
        self.tabs.addTab(tab_temp, "温度控制")

        # Tab 3: 泵控制
        tab_pump = build_pump_tab(self)
        self.tabs.addTab(tab_pump, "泵控制")

        # Tab 4: 其他设置 (move all controls here)
        tab_misc = QWidget(self)
        tab4_layout = QVBoxLayout(tab_misc)

        # Camera mode row (fluorescence / mono)
        self.camera_mode_fluorescence = True
        self.cam_mode_btn = QPushButton("荧光", self)
        self.cam_mode_btn.setCheckable(True)
        self.cam_mode_btn.setChecked(True)
        self.cam_mode_btn.toggled.connect(self._on_cam_mode_toggled)
        m0 = QHBoxLayout()
        m0.addWidget(QLabel("摄像头模式:"))
        m0.addStretch(1)
        m0.addWidget(self.cam_mode_btn)
        tab4_layout.addLayout(m0)

        # Exposure controls row
        m1 = QHBoxLayout()
        m1.addWidget(QLabel("Exposure Auto:"))
        m1.addWidget(self.exposure_auto_cb)
        m1.addWidget(QLabel("Exposure:"))
        m1.addWidget(self.exposure_slider, 1)
        m1.addWidget(self.exposure_spin)
        tab4_layout.addLayout(m1)

        # Gain controls row
        m2 = QHBoxLayout()
        m2.addWidget(QLabel("Gain Auto:"))
        m2.addWidget(self.gain_auto_cb)
        m2.addWidget(QLabel("Gain:"))
        m2.addWidget(self.gain_slider, 1)
        m2.addWidget(self.gain_spin)
        tab4_layout.addLayout(m2)

        # Options row (gamma/enhance)
        m3 = QHBoxLayout()
        m3.addWidget(self.gamma_chk)
        m3.addSpacing(12)
        m3.addWidget(self.enhance_chk)
        m3.addStretch(1)
        tab4_layout.addLayout(m3)

        # Image save path chooser
        self.image_save_dir = os.path.expanduser("~/Pictures")
        self.save_path_edit = QLineEdit(self)
        self.save_path_edit.setReadOnly(True)
        self.save_path_edit.setText(self.image_save_dir)
        self.save_path_btn = QPushButton("选择路径…", self)
        self.save_path_btn.clicked.connect(self._choose_save_dir)
        m_path = QHBoxLayout()
        m_path.addWidget(QLabel("图片保存路径:"))
        m_path.addWidget(self.save_path_edit, 1)
        m_path.addWidget(self.save_path_btn)
        tab4_layout.addLayout(m_path)

        # Place Start/Stop at bottom
        tab4_layout.addSpacing(self.s(8))
        tab4_layout.addWidget(self.ui.pushButton)
        self.tabs.addTab(tab_misc, "其他设置")

        # Configure button
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.clicked.connect(self.toggle_start_stop)

        # Unified dark stylesheet with proportionally larger controls
        btn_min_h = self.s(32)
        groove_h = max(7, int(self.s(9)))
        handle_w = max(14, int(self.s(18)))
        handle_margin = -max(6, int(self.s(7)))
        self.setStyleSheet(
            f"QWidget {{ background-color: #1b1f23; color: #cdd3da; font-size: {int(13*self._ui_scale)}px; }}"
            "QLabel { color: #cdd3da; }"
            "#card { background-color: #22262b; border: 1px solid #343a40; border-radius: 10px; }"
            "#card QLabel { background: transparent; }"
            "#cardHeader { background: transparent; }"
            "#cardIcon { font-size: 20px; background: transparent; }"
            "#cardTitle { background: transparent; }"
            f"QPushButton {{ background-color: #2b2f34; color: #e6e9ee; border: 1px solid #3a3f45; border-radius: 8px; padding: 6px 12px; min-height: {btn_min_h}px; }}"
            "QPushButton:hover { background-color: #32373d; }"
            "QPushButton:checked { background-color: #2e5f97; border-color: #2e5f97; }"
            "QPushButton:disabled { color: #858c94; }"
            f"QSlider::groove:horizontal {{ height: {groove_h}px; background: #353a40; border-radius: {groove_h//2}px; }}"
            f"QSlider::handle:horizontal {{ background: #2e5f97; width: {handle_w}px; margin: {handle_margin}px 0; border-radius: {handle_w//2}px; }}"
            "QSlider::sub-page:horizontal { background: #2e5f97; }"
            # Segmented buttons
            "QPushButton#segLeft { border-top-right-radius: 0; border-bottom-right-radius: 0; border-right: none; }"
            "QPushButton#segMid { border-radius: 0; border-right: none; }"
            "QPushButton#segRight { border-top-left-radius: 0; border-bottom-left-radius: 0; }"
            # Nudge buttons (ghost pills)
            "#nudgeUp, #nudgeDown, #nudgeLeft, #nudgeRight { background: transparent; border: 1px solid #495059; color: #cfd6de; }"
            "#nudgeUp, #nudgeDown { border-radius: 10px; padding: 2px 8px; }"
            "#nudgeLeft, #nudgeRight { border-radius: 10px; padding: 8px 2px; }"
            "#nudgeUp:hover, #nudgeDown:hover, #nudgeLeft:hover, #nudgeRight:hover { background: rgba(255,255,255,0.04); border-color: #5a636e; }"
            "#nudgeUp:pressed, #nudgeDown:pressed, #nudgeLeft:pressed, #nudgeRight:pressed { background: rgba(46,95,151,0.15); border-color: #2e5f97; color: #e8f1ff; }"
        )

        # Make channel segmented group slightly bolder font (guarded for pixel-size fonts)
        for b in self.channel_buttons:
            bf = b.font()
            pt = bf.pointSizeF()
            if pt > 0:
                bf.setPointSizeF(max(1.0, pt + 0.5))
            else:
                px = bf.pixelSize()
                if px > 0:
                    bf.setPixelSize(px + 1)
            b.setFont(bf)

        # Default UI states
        self.exposure_auto_cb.setCurrentText("Continuous")
        self.gain_auto_cb.setCurrentText("Continuous")
        self.gamma_chk.setChecked(False)
        self._set_exposure_controls_enabled(False)
        self._set_gain_controls_enabled(False)

        # React to UI changes (send to worker when available)
        self.exposure_auto_cb.currentTextChanged.connect(self._on_exposure_auto_changed)
        self.exposure_spin.valueChanged.connect(self._on_exposure_changed)
        self.gain_auto_cb.currentTextChanged.connect(self._on_gain_auto_changed)
        self.gain_spin.valueChanged.connect(self._on_gain_changed)
        self.gamma_chk.toggled.connect(self._on_gamma_toggled)
        self.enhance_chk.toggled.connect(self._on_enhance_toggled)

    def _set_exposure_controls_enabled(self, enabled: bool):
        self.exposure_slider.setEnabled(enabled)
        self.exposure_spin.setEnabled(enabled)

    def _set_gain_controls_enabled(self, enabled: bool):
        self.gain_slider.setEnabled(enabled)
        self.gain_spin.setEnabled(enabled)

    def toggle_start_stop(self):
        if not self.streaming:
            self.start_camera()
        else:
            self.stop_camera()

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.worker = CameraWorker()
        self.worker.frameReady.connect(self.on_frame)
        self.worker.error.connect(self.on_error)
        self.worker.startedStreaming.connect(lambda: self.ui.pushButton.setText("Stop"))
        self.worker.stoppedStreaming.connect(lambda: self.ui.pushButton.setText("Start"))
        self.streaming = True
        self.ui.pushButton.setText("Starting...")
        self.worker.start()

        # Apply current UI settings to camera
        self._apply_all_controls_to_worker()

    def stop_camera(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self.streaming = False
        self.ui.pushButton.setText("Start")

    def on_frame(self, arr: np.ndarray, w: int, h: int, bytes_per_line: int):
        # arr is already an owned numpy array (Mono8). Optionally enhance contrast.
        try:
            if self.enhance_contrast:
                arr = cv2.equalizeHist(arr)
            qimg = QImage(arr.data, w, h, bytes_per_line, QImage.Format_Grayscale8).copy()
            self._last_qimage = qimg
            self.update_video_label()
        except Exception:
            qimg = QImage(arr.tobytes(), w, h, w, QImage.Format_Grayscale8).copy()
            self._last_qimage = qimg
            self.update_video_label()

    def on_error(self, msg: str):
        self.image_label.setText(f"Error: {msg}")
        self.stop_camera()

    def closeEvent(self, event):
        try:
            self.stop_camera()
        finally:
            return super().closeEvent(event)

    # --- Responsive rendering helpers ---
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep a larger right panel when maximized
        if self.window().isMaximized():
            total_w = max(0, self.width())
            # keep right panel around target width or ~38% of total, within [min,max]
            min_w = self.s(520)
            max_w = self.s(760)
            pref = max(min_w, min(self._right_target_width, max_w))
            frac = 0.38
            right_w = int(max(min_w, min(max_w, max(pref, total_w * frac))))
            left_w = max(self.s(360), total_w - right_w - 16)
            self.splitter.setSizes([left_w, right_w])
            # tighten first row height when maximized
            self.first_row_widget.setMaximumHeight(self.s(200))
        else:
            # relax height when normal size
            self.first_row_widget.setMaximumHeight(self.s(240))
        self.update_video_label()

    def update_video_label(self):
        if self._last_qimage is None:
            return
        # Scale to fit while preserving aspect ratio and smooth transform
        target = self.image_label.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        pm = QPixmap.fromImage(self._last_qimage).scaled(
            target,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pm)

    # ----- UI -> Worker handlers -----
    def _apply_all_controls_to_worker(self):
        if not self.worker:
            return
        # Exposure
        mode = self.exposure_auto_cb.currentText()
        self.worker.setExposureAuto.emit(mode)
        if mode == "Off":
            self.worker.setExposureTime.emit(float(self.exposure_spin.value()))
        # Gain
        gmode = self.gain_auto_cb.currentText()
        self.worker.setGainAuto.emit(gmode)
        if gmode == "Off":
            self.worker.setGain.emit(self.gain_spin.value() / 10.0)
        # Gamma
        self.worker.setGammaEnable.emit(self.gamma_chk.isChecked())

    def _on_exposure_auto_changed(self, text: str):
        off = (text == "Off")
        self._set_exposure_controls_enabled(off)
        if self.worker:
            self.worker.setExposureAuto.emit(text)
            if off:
                self.worker.setExposureTime.emit(float(self.exposure_spin.value()))

    def _on_exposure_changed(self, val: int):
        if self.worker and self.exposure_auto_cb.currentText() == "Off":
            self.worker.setExposureTime.emit(float(val))

    def _on_gain_auto_changed(self, text: str):
        off = (text == "Off")
        self._set_gain_controls_enabled(off)
        if self.worker:
            self.worker.setGainAuto.emit(text)
            if off:
                self.worker.setGain.emit(self.gain_spin.value() / 10.0)

    def _on_gain_changed(self, val: int):
        if self.worker and self.gain_auto_cb.currentText() == "Off":
            self.worker.setGain.emit(val / 10.0)

    def _on_gamma_toggled(self, checked: bool):
        if self.worker:
            self.worker.setGammaEnable.emit(checked)

    def _on_enhance_toggled(self, checked: bool):
        self.enhance_contrast = checked

    # --- Misc tab handlers ---
    def _on_cam_mode_toggled(self, on: bool):
        # True -> 荧光, False -> 黑白
        self.camera_mode_fluorescence = on
        self.cam_mode_btn.setText("荧光" if on else "黑白")
        # If future: notify worker about color mode
        # if self.worker:
        #     self.worker.setColorMode.emit("fluorescence" if on else "mono")

    def _choose_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片保存路径", self.image_save_dir)
        if d:
            self.image_save_dir = d
            self.save_path_edit.setText(d)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
