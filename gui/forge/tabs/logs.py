# gui/tabs/logs.py
"""Logs tab — stream and display Forgejo service logs."""

from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)


class LogsTab(QWidget):
    """📄 Logs tab widget.

    Exposes the log view widget and the toggle button so MainWindow
    can drive log streaming.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── public interface ──────────────────────────────────────────────

    def n_lines(self) -> int:
        return self.inp_lines.value()

    def follow_checked(self) -> bool:
        return self.chk_follow.isChecked()

    def clear_log(self):
        self.log_view.clear()

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        opts = QHBoxLayout()
        self.chk_follow = QCheckBox("Follow (-f)")
        self.chk_follow.setChecked(True)
        opts.addWidget(self.chk_follow)

        opts.addWidget(QLabel("Lines"))
        self.inp_lines = QSpinBox()
        self.inp_lines.setRange(10, 1000)
        self.inp_lines.setValue(50)
        self.inp_lines.setFixedWidth(120)
        opts.addWidget(self.inp_lines)
        opts.addStretch()

        self.btn_logs = QPushButton("📄  Show Logs")
        self.btn_logs.setObjectName("btn_logs")
        opts.addWidget(self.btn_logs)
        lay.addLayout(opts)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs will appear here...")
        lay.addWidget(self.log_view, stretch=1)
