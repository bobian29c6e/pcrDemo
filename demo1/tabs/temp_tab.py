from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
    QFrame,
    QSizePolicy,
)


def build_temp_tab(parent) -> QWidget:
    """Build the 温度控制 tab UI with three rows:
    1) Current temperatures (Left/Right)
    2) Setpoint inputs with external up/down buttons (0.1 step)
    3) Left/Right heater switches (pill buttons)
    """
    tab = QWidget(parent)
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)

    # Two symmetric panels
    row = QHBoxLayout()
    row.setSpacing(20)

    def make_panel(title: str, switch_obj: str):
        panel = QFrame(tab)
        panel.setObjectName("tempPanel")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        panel.setMinimumHeight(240)
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(16, 14, 22, 14)
        pv.setSpacing(12)

        header = QLabel(title, panel)
        header.setObjectName("panelTitle")
        pv.addWidget(header)

        value = QLabel("--.- °C", panel)
        value.setObjectName("panelValue")
        pv.addWidget(value)
        # subtle divider
        divider = QFrame(panel)
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setObjectName("tempDivider")
        pv.addWidget(divider)

        # setpoint block (label on top; below is spin + nudge; confirm on its own row)
        sp_block = QVBoxLayout()
        sp_block.setContentsMargins(0, 0, 0, 0)
        sp_block.setSpacing(8)

        sp_label = QLabel("设定温度", panel)
        sp_block.addWidget(sp_label)

        sp_line = QHBoxLayout()
        sp_line.setContentsMargins(0, 0, 0, 0)
        sp_line.setSpacing(10)
        spin = QDoubleSpinBox(panel)
        spin.setDecimals(1)
        spin.setSingleStep(0.1)
        spin.setRange(0.0, 120.0)
        spin.setSuffix(" °C")
        spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        spin.setMinimumWidth(140)
        spin.setMaximumWidth(160)
        # compact framed nudge column
        nudge_frame = QFrame(panel)
        nudge_frame.setObjectName("nudgeFrame")
        nudge_frame.setFixedWidth(60)
        nudge_frame.setMaximumWidth(68)
        nudge_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        nudge_col = QVBoxLayout(nudge_frame)
        # symmetric inner margins so left/right gaps look the same
        nudge_col.setContentsMargins(6, 5, 6, 5)
        nudge_col.setSpacing(3)
        nudge_col.setAlignment(Qt.AlignHCenter)
        up_btn = QPushButton("▲", nudge_frame)
        dn_btn = QPushButton("▼", nudge_frame)
        for b in (up_btn, dn_btn):
            b.setMinimumHeight(16)
            b.setMinimumWidth(40)
            b.setMaximumWidth(40)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            b.setObjectName("tempNudge")
        up_btn.clicked.connect(lambda: spin.setValue(round(spin.value() + 0.1, 1)))
        dn_btn.clicked.connect(lambda: spin.setValue(round(spin.value() - 0.1, 1)))
        nudge_col.addWidget(up_btn)
        nudge_col.addWidget(dn_btn)
        sp_line.addWidget(spin)
        sp_line.addStretch(1)
        sp_line.addWidget(nudge_frame, 0, Qt.AlignVCenter)
        sp_line.addSpacing(8)
        sp_block.addLayout(sp_line)

        confirm_row = QHBoxLayout()
        confirm_row.setContentsMargins(0, 0, 0, 0)
        confirm_row.setSpacing(0)
        confirm_row.addStretch(1)
        confirm_btn = QPushButton("确认", panel)
        confirm_btn.setObjectName("tempConfirm")
        confirm_btn.setMinimumHeight(30)
        confirm_btn.setMinimumWidth(86)
        confirm_row.addWidget(confirm_btn)
        confirm_row.addStretch(1)
        sp_block.addLayout(confirm_row)

        pv.addLayout(sp_block)

        # centered pill switch
        sw_row = QHBoxLayout()
        sw_row.setContentsMargins(0, 0, 0, 0)
        sw_row.setSpacing(8)
        sw_row.addStretch(1)
        sw_btn = QPushButton("OFF", panel)
        sw_btn.setCheckable(True)
        sw_btn.setObjectName(switch_obj)
        sw_btn.setMinimumHeight(34)
        sw_btn.setMinimumWidth(92)
        sw_btn.toggled.connect(lambda on, b=sw_btn: b.setText("ON" if on else "OFF"))
        sw_row.addWidget(sw_btn)
        sw_row.addStretch(1)
        pv.addLayout(sw_row)

        return panel, value, spin, sw_btn, confirm_btn

    left_panel, left_val, left_set_spin, left_switch, left_confirm = make_panel("左侧加热板", "leftSwitch")
    right_panel, right_val, right_set_spin, right_switch, right_confirm = make_panel("右侧加热板", "rightSwitch")

    row.addWidget(left_panel, 1)
    row.addSpacing(12)
    row.addWidget(right_panel, 1)
    layout.addLayout(row)

    # Local stylesheet to beautify
    tab.setStyleSheet(
        "#tempPanel { background: #202429; border: 1px solid #2d3339; border-radius: 12px; }"
        "#tempPanel QPushButton, #tempPanel QDoubleSpinBox, #tempPanel QLabel { background: transparent; }"
        "#panelTitle { color: #b8c0c9; font-weight: 600; letter-spacing: 0.2px; }"
        "#panelValue { color: #eef3f9; font-size: 26px; font-weight: 800; padding: 2px 0 4px; }"
        "QDoubleSpinBox { background: #1c2126; border: 1px solid #343a41; border-radius: 10px; padding: 8px 12px; color: #e6e9ee; min-width: 140px; }"
        "QDoubleSpinBox:focus { border-color: #2e5f97; }"
        "#nudgeFrame { background: #1e2328; border: 1px solid #2e343b; border-radius: 8px; }"
        "QPushButton#tempNudge { background: transparent; border: 1px solid #3a3f45; border-radius: 6px; color: #d5dbe3; min-width: 45px; max-width: 45px; padding: 0; margin: 0; }"
        "QPushButton#tempNudge:hover { background: #2a2f36; }"
        "QPushButton#tempNudge:pressed { background: #2e5f97; border-color: #2e5f97; color: #e8f1ff; }"
        "QPushButton#leftSwitch, QPushButton#rightSwitch { background: #2a2f35; color: #e6e9ee; border: 1px solid #3a3f45; border-radius: 18px; padding: 8px 18px; min-width: 92px; }"
        "QPushButton#leftSwitch:checked, QPushButton#rightSwitch:checked { background: #2e5f97; border-color: #2e5f97; }"
        "QPushButton#tempConfirm { background: transparent; color: #9fc2f3; border: 1px solid #2e5f97; border-radius: 16px; padding: 4px 12px; }"
        "QPushButton#tempConfirm:hover { background: rgba(46,95,151,0.15); }"
        "QPushButton#tempConfirm:pressed { background: rgba(46,95,151,0.28); }"
    )

    # keep content top-aligned
    layout.addStretch(1)

    # Expose refs on tab for later wiring
    tab.left_temp_value = left_val
    tab.right_temp_value = right_val
    tab.left_set_spin = left_set_spin
    tab.right_set_spin = right_set_spin
    tab.left_switch = left_switch
    tab.right_switch = right_switch
    tab.left_confirm_btn = left_confirm
    tab.right_confirm_btn = right_confirm

    return tab
