# gui/tabs/control.py
"""Control tab — start / stop / restart / uninstall."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from forge.constants import FG_SUBTLE, RED


class ControlTab(QWidget):
    """▶ Control tab widget.

    Owns the service-control buttons and the status / instance-info display.
    MainWindow connects the button signals and calls ``set_info_text()``.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── public interface ──────────────────────────────────────────────

    def set_info_text(self, text: str):
        self.info_text.setText(text.strip() or "No output.")

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        lay   = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        lay.addWidget(self._make_service_group())
        lay.addWidget(self._make_info_group())
        lay.addWidget(self._make_danger_group())
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        outer.addWidget(scroll)

    def _make_service_group(self) -> QGroupBox:
        grp = QGroupBox("Service control")
        lay = QHBoxLayout(grp)
        lay.setSpacing(10)

        for obj_name, label in [
            ("btn_start",   "▶  Start"),
            ("btn_stop",    "■  Stop"),
            ("btn_restart", "↺  Restart"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(52)
            lay.addWidget(btn)
            setattr(self, obj_name, btn)

        return grp

    def _make_info_group(self) -> QGroupBox:
        grp = QGroupBox("Instance info")
        lay = QVBoxLayout(grp)

        self.info_text = QLabel("Run 'status' or wait for auto-refresh.")
        self.info_text.setStyleSheet(f"color: {FG_SUBTLE}; font-size: 24px;")
        self.info_text.setWordWrap(True)
        lay.addWidget(self.info_text)

        self.btn_refresh = QPushButton("⟳  Refresh status")
        lay.addWidget(self.btn_refresh)

        return grp

    def _make_danger_group(self) -> QGroupBox:
        grp = QGroupBox("Danger zone")
        grp.setStyleSheet(f"QGroupBox {{ border-color: {RED}; color: {RED}; }}")
        lay = QVBoxLayout(grp)

        self.btn_uninstall = QPushButton("🗑  Uninstall Forgejo")
        self.btn_uninstall.setObjectName("btn_uninstall")
        self.btn_uninstall.setFixedHeight(52)
        lay.addWidget(self.btn_uninstall)

        return grp
