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


def build_pump_tab(parent) -> QWidget:
    """Build the 泵控制 tab UI with four rows:
    1) 当前值（左/右泵）
    2) 设定压力（1/2通道）
    3) 两个泵的开关
    4) 联动开关
    风格与温控页保持一致的深色卡片化设计。
    """
    tab = QWidget(parent)
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)

    # --- Two symmetric panels (Channel 1 / Channel 2) ---
    row = QHBoxLayout()
    row.setSpacing(20)

    def make_panel(title: str, switch_obj: str):
        panel = QFrame(tab)
        panel.setObjectName("pumpPanel")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        panel.setMinimumHeight(240)
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(16, 14, 22, 14)
        pv.setSpacing(12)

        header = QLabel(title, panel)
        header.setObjectName("panelTitle")
        pv.addWidget(header)

        value = QLabel("--.- kPa", panel)
        value.setObjectName("panelValue")
        pv.addWidget(value)

        divider = QFrame(panel)
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setObjectName("pumpDivider")
        pv.addWidget(divider)

        # Setpoint block
        sp_block = QVBoxLayout()
        sp_block.setContentsMargins(0, 0, 0, 0)
        sp_block.setSpacing(8)

        sp_label = QLabel("设定压力", panel)
        sp_block.addWidget(sp_label)

        sp_line = QHBoxLayout()
        sp_line.setContentsMargins(0, 0, 0, 0)
        sp_line.setSpacing(10)
        spin = QDoubleSpinBox(panel)
        spin.setDecimals(1)
        spin.setSingleStep(0.1)
        spin.setRange(0.0, 200.0)
        spin.setSuffix(" kPa")
        spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        spin.setMinimumWidth(140)
        spin.setMaximumWidth(160)

        # Nudge column (same look-and-feel)
        nudge_frame = QFrame(panel)
        nudge_frame.setObjectName("nudgeFrame")
        nudge_frame.setFixedWidth(60)
        nudge_frame.setMaximumWidth(68)
        nudge_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        nudge_col = QVBoxLayout(nudge_frame)
        nudge_col.setContentsMargins(6, 5, 6, 5)
        nudge_col.setSpacing(3)
        nudge_col.setAlignment(Qt.AlignHCenter)
        up_btn = QPushButton("▲", nudge_frame)
        dn_btn = QPushButton("▼", nudge_frame)
        for b in (up_btn, dn_btn):
            b.setMinimumHeight(16)
            b.setMinimumWidth(30)
            b.setMaximumWidth(36)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            b.setObjectName("pumpNudge")
        up_btn.clicked.connect(lambda: spin.setValue(round(spin.value() + 0.1, 1)))
        dn_btn.clicked.connect(lambda: spin.setValue(round(spin.value() - 0.1, 1)))
        nudge_col.addWidget(up_btn)
        nudge_col.addWidget(dn_btn)

        sp_line.addWidget(spin)
        sp_line.addStretch(1)
        sp_line.addWidget(nudge_frame, 0, Qt.AlignVCenter)
        sp_line.addSpacing(8)
        sp_block.addLayout(sp_line)

        # Confirm centered under input
        confirm_row = QHBoxLayout()
        confirm_row.setContentsMargins(0, 0, 0, 0)
        confirm_row.setSpacing(0)
        confirm_row.addStretch(1)
        confirm_btn = QPushButton("确认", panel)
        confirm_btn.setObjectName("pumpConfirm")
        confirm_btn.setMinimumHeight(30)
        confirm_btn.setMinimumWidth(86)
        confirm_row.addWidget(confirm_btn)
        confirm_row.addStretch(1)
        sp_block.addLayout(confirm_row)

        pv.addLayout(sp_block)

        # Pump switch (pill) centered
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

    left_panel, p1_value, p1_spin, p1_switch, p1_confirm = make_panel("1通道泵", "pump1Switch")
    right_panel, p2_value, p2_spin, p2_switch, p2_confirm = make_panel("2通道泵", "pump2Switch")

    row.addWidget(left_panel, 1)
    row.addSpacing(12)
    row.addWidget(right_panel, 1)
    layout.addLayout(row)

    # --- Linkage switch row (bottom) ---
    link_row = QHBoxLayout()
    link_row.setContentsMargins(0, 0, 0, 0)
    link_row.setSpacing(8)
    link_row.addStretch(1)
    link_btn = QPushButton("联动: OFF", tab)
    link_btn.setCheckable(True)
    link_btn.setObjectName("pumpLinkSwitch")
    link_btn.setMinimumHeight(32)
    link_btn.setMinimumWidth(110)
    link_btn.toggled.connect(lambda on: link_btn.setText(f"联动: {'ON' if on else 'OFF'}"))
    link_row.addWidget(link_btn)
    link_row.addStretch(1)
    layout.addLayout(link_row)

    # Styling (match temperature tab aesthetics)
    tab.setStyleSheet(
        "#pumpPanel { background: #202429; border: 1px solid #2d3339; border-radius: 12px; }"
        "#pumpPanel QPushButton, #pumpPanel QDoubleSpinBox, #pumpPanel QLabel { background: transparent; }"
        "#panelTitle { color: #b8c0c9; font-weight: 600; letter-spacing: 0.2px; }"
        "#panelValue { color: #eef3f9; font-size: 26px; font-weight: 800; padding: 2px 0 4px; }"
        "QDoubleSpinBox { background: #1c2126; border: 1px solid #343a41; border-radius: 10px; padding: 8px 12px; color: #e6e9ee; min-width: 140px; }"
        "QDoubleSpinBox:focus { border-color: #2e5f97; }"
        "#nudgeFrame { background: #1e2328; border: 1px solid #2e343b; border-radius: 8px; }"
        "QPushButton#pumpNudge { background: transparent; border: 1px solid #3a3f45; border-radius: 6px; color: #d5dbe3; min-width: 30px; max-width: 36px; padding: 0; margin: 0; }"
        "QPushButton#pumpNudge:hover { background: #2a2f36; }"
        "QPushButton#pumpNudge:pressed { background: #2e5f97; border-color: #2e5f97; color: #e8f1ff; }"
        "QPushButton#pump1Switch, QPushButton#pump2Switch { background: #2a2f35; color: #e6e9ee; border: 1px solid #3a3f45; border-radius: 18px; padding: 8px 18px; min-width: 92px; }"
        "QPushButton#pump1Switch:checked, QPushButton#pump2Switch:checked { background: #2e5f97; border-color: #2e5f97; }"
        "QPushButton#pumpConfirm { background: transparent; color: #9fc2f3; border: 1px solid #2e5f97; border-radius: 16px; padding: 4px 12px; }"
        "QPushButton#pumpConfirm:hover { background: rgba(46,95,151,0.15); }"
        "QPushButton#pumpConfirm:pressed { background: rgba(46,95,151,0.28); }"
        "QPushButton#pumpLinkSwitch { background: #2b3036; color: #e6e9ee; border: 1px solid #3a3f45; border-radius: 18px; padding: 6px 16px; }"
        "QPushButton#pumpLinkSwitch:checked { background: #2e5f97; border-color: #2e5f97; }"
    )

    # Expose refs on tab for wiring outside
    tab.p1_value = p1_value
    tab.p2_value = p2_value
    tab.p1_set_spin = p1_spin
    tab.p2_set_spin = p2_spin
    tab.p1_switch = p1_switch
    tab.p2_switch = p2_switch
    tab.p1_confirm_btn = p1_confirm
    tab.p2_confirm_btn = p2_confirm
    tab.link_switch = link_btn

    # --- Linkage behavior ---
    def _sync_spin(src: QDoubleSpinBox, dst: QDoubleSpinBox):
        if abs(dst.value() - src.value()) < 1e-6:
            return
        was = dst.blockSignals(True)
        try:
            dst.setValue(src.value())
        finally:
            dst.blockSignals(was)

    def _sync_switch(src: QPushButton, dst: QPushButton):
        if dst.isChecked() == src.isChecked():
            return
        was = dst.blockSignals(True)
        try:
            dst.setChecked(src.isChecked())
        finally:
            dst.blockSignals(was)

    # When spins change and link is ON, keep them equal
    p1_spin.valueChanged.connect(lambda _v: _sync_spin(p1_spin, p2_spin) if link_btn.isChecked() else None)
    p2_spin.valueChanged.connect(lambda _v: _sync_spin(p2_spin, p1_spin) if link_btn.isChecked() else None)

    # When switches toggle and link is ON, mirror the other
    p1_switch.toggled.connect(lambda _on: _sync_switch(p1_switch, p2_switch) if link_btn.isChecked() else None)
    p2_switch.toggled.connect(lambda _on: _sync_switch(p2_switch, p1_switch) if link_btn.isChecked() else None)

    # When link is enabled, immediately align CH2 to CH1 (value + switch)
    link_btn.toggled.connect(lambda on: (_sync_spin(p1_spin, p2_spin), _sync_switch(p1_switch, p2_switch)) if on else None)

    # Keep content top-aligned
    layout.addStretch(1)

    return tab
