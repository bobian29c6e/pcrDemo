from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

def build_pump_tab(parent) -> QWidget:
    """Build the 泵控制 tab. Placeholder to be filled with existing widgets."""
    tab = QWidget(parent)
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    layout.addWidget(QLabel("泵控制 – 待迁移", tab, alignment=Qt.AlignCenter))
    return tab
