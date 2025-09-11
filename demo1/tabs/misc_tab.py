from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

def build_misc_tab(parent) -> QWidget:
    """Build the 其他设置 tab. Placeholder to be filled with existing widgets."""
    tab = QWidget(parent)
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    layout.addWidget(QLabel("其他设置 – 待迁移", tab, alignment=Qt.AlignCenter))
    return tab
