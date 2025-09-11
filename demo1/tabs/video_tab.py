from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QButtonGroup,
    QSizePolicy,
    QSpacerItem,
)

# External widgets/factories
from widgets.grid_preview import GridPreviewWidget
from widgets.arrow_buttons import make_arrow_btn


def build_video_tab(parent, s, make_card):
    """
    Build the '画面控制' tab and return (tab_widget, refs).
    - refs contains: grid, obj_group, obj_buttons, channel_group, channel_buttons
    - Caller wires signals and places into a scroll area if desired.
    """
    tab = QWidget(parent)
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    # Row 1: Big box (grid) centered, arrows around
    first_row_widget = QWidget(tab)
    row1 = QGridLayout(first_row_widget)
    row1.setContentsMargins(0, 0, 0, 0)
    row1.setHorizontalSpacing(8)
    row1.setVerticalSpacing(6)

    grid = GridPreviewWidget(first_row_widget)
    up_btn = make_arrow_btn(first_row_widget, 'Up', 82, 20, s)
    down_btn = make_arrow_btn(first_row_widget, 'Down', 82, 20, s)
    left_btn = make_arrow_btn(first_row_widget, 'Left', 20, 82, s)
    right_btn = make_arrow_btn(first_row_widget, 'Right', 20, 82, s)

    # layout arrows around center grid
    row1.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 0)
    row1.addWidget(up_btn, 0, 1, alignment=Qt.AlignHCenter | Qt.AlignBottom)
    row1.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 0, 2)

    row1.addWidget(left_btn, 1, 0, alignment=Qt.AlignVCenter | Qt.AlignRight)
    row1.addWidget(grid, 1, 1)
    row1.addWidget(right_btn, 1, 2, alignment=Qt.AlignVCenter | Qt.AlignLeft)

    row1.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)
    row1.addWidget(down_btn, 2, 1, alignment=Qt.AlignHCenter | Qt.AlignTop)
    row1.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 2)

    first_row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    first_row_widget.setMaximumHeight(s(220))
    layout.addWidget(first_row_widget)

    # Arrow nudges
    step = 0.08
    up_btn.clicked.connect(lambda: grid.nudge(0, -step))
    down_btn.clicked.connect(lambda: grid.nudge(0, step))
    left_btn.clicked.connect(lambda: grid.nudge(-step, 0))
    right_btn.clicked.connect(lambda: grid.nudge(step, 0))

    # Row 1.5: objective magnification segmented buttons
    row_mag = QHBoxLayout()
    row_mag.setSpacing(0)
    row_mag.setContentsMargins(4, 0, 4, 0)
    obj_group = QButtonGroup(tab)
    obj_group.setExclusive(True)
    obj_buttons = []
    for idx, name in enumerate(["2X", "4X", "10X", "20X", "40X"]):
        btn = QPushButton(name, tab)
        btn.setCheckable(True)
        obj_group.addButton(btn)
        obj_buttons.append(btn)
        if idx == 0:
            btn.setObjectName("segLeft")
        elif idx == 4:
            btn.setObjectName("segRight")
        else:
            btn.setObjectName("segMid")
        btn.setMinimumHeight(s(34))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setMinimumWidth(s(64))
        btn.setMaximumWidth(s(84))
        row_mag.addWidget(btn)
    # default 10X
    for b in obj_buttons:
        if b.text() == "10X":
            b.setChecked(True)
            break
    row_mag.insertStretch(0, 1)
    row_mag.addStretch(1)
    layout.addLayout(row_mag)

    # Row 2: fluorescence channel buttons (segmented)
    row2 = QHBoxLayout()
    row2.setSpacing(0)
    row2.setContentsMargins(4, 0, 4, 0)
    channel_group = QButtonGroup(tab)
    channel_group.setExclusive(True)
    channel_buttons = []
    channel_names = ["DAPI", "GFP", "RFP", "TX RED", "Trans"]
    for idx, name in enumerate(channel_names):
        btn = QPushButton(name, tab)
        btn.setCheckable(True)
        channel_group.addButton(btn)
        channel_buttons.append(btn)
        if idx == 0:
            btn.setObjectName("segLeft")
        elif idx == len(channel_names) - 1:
            btn.setObjectName("segRight")
        else:
            btn.setObjectName("segMid")
        btn.setMinimumHeight(s(38))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setMinimumWidth(s(96))
        btn.setMaximumWidth(s(124))
        row2.addWidget(btn)
    # default channel
    if channel_buttons:
        channel_buttons[0].setChecked(True)
    layout.addLayout(row2)

    # Row 3: Light card
    light_card, light_layout = make_card("Light", "💡")
    row3 = QHBoxLayout()
    row3.setContentsMargins(0, 0, 0, 0)
    row3.setSpacing(10)
    light_btn = QPushButton("光源: OFF", tab)
    light_btn.setCheckable(True)
    light_btn.toggled.connect(lambda on: light_btn.setText(f"光源: {'ON' if on else 'OFF'}"))
    row3.addWidget(light_btn)
    row3.addSpacing(12)
    bright_lbl = QLabel("Bright:")
    bright_lbl.setMinimumWidth(48)
    row3.addWidget(bright_lbl)
    aperture_slider = QSlider(Qt.Horizontal)
    aperture_slider.setRange(0, 100)
    row3.addWidget(aperture_slider, 1)
    light_layout.addLayout(row3)
    fixed_h1 = s(110)
    light_card.setMinimumHeight(fixed_h1)
    light_card.setMaximumHeight(fixed_h1)
    light_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(light_card)

    # Row 4: Autofocus card
    af_card, af_layout = make_card("Autofocus", "⚙️")
    row4 = QHBoxLayout()
    row4.setContentsMargins(0, 0, 0, 0)
    row4.setSpacing(10)
    af_btn = QPushButton("自动聚焦", tab)
    row4.addWidget(af_btn)
    row4.addSpacing(12)
    focus_box = QVBoxLayout()
    focus_box.addWidget(QLabel("Coarse"))
    focus_coarse = QSlider(Qt.Horizontal)
    focus_coarse.setRange(-1000, 1000)
    focus_box.addWidget(focus_coarse)
    focus_box.addWidget(QLabel("Fine"))
    focus_fine = QSlider(Qt.Horizontal)
    focus_fine.setRange(-100, 100)
    focus_box.addWidget(focus_fine)
    row4.addLayout(focus_box, 1)
    af_layout.addLayout(row4)
    fixed_h2 = s(140)
    af_card.setMinimumHeight(fixed_h2)
    af_card.setMaximumHeight(fixed_h2)
    af_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(af_card)

    # Row 5: Capture card
    cap_card, cap_layout = make_card("Capture", "📷")
    row5 = QHBoxLayout()
    capture_btn = QPushButton("拍照", tab)
    row5.addWidget(capture_btn)
    row5.addStretch(1)
    right_btns = QVBoxLayout()
    clear_positions_btn = QPushButton("清空拍摄位置", tab)
    save_image_btn = QPushButton("存储图片", tab)
    right_btns.addWidget(clear_positions_btn)
    right_btns.addWidget(save_image_btn)
    row5.addLayout(right_btns)
    cap_layout.addLayout(row5)
    fixed_h3 = s(110)
    cap_card.setMinimumHeight(fixed_h3)
    cap_card.setMaximumHeight(fixed_h3)
    cap_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(cap_card)

    refs = {
        "grid": grid,
        "obj_group": obj_group,
        "obj_buttons": obj_buttons,
        "channel_group": channel_group,
        "channel_buttons": channel_buttons,
        "first_row_widget": first_row_widget,
        # cards & controls
        "light_btn": light_btn,
        "aperture_slider": aperture_slider,
        "af_btn": af_btn,
        "focus_coarse": focus_coarse,
        "focus_fine": focus_fine,
        "capture_btn": capture_btn,
        "clear_positions_btn": clear_positions_btn,
        "save_image_btn": save_image_btn,
    }
    return tab, refs
