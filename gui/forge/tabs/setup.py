# gui/tabs/setup.py
"""Setup tab — admin credentials, server settings, app.ini editor."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from forge.constants import FG_SUBTLE


class SetupTab(QWidget):
    """⚙ Setup tab widget.

    Owns all setup-related input fields and exposes:
      - ``get_setup_args()``     → CLI args for 'setup'
      - ``apply_actions_now()``  → signal-like callback (set by MainWindow)
      - ``open_ini_editor()``    → signal-like callback (set by MainWindow)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── public interface used by MainWindow ───────────────────────────

    def get_setup_args(self) -> list[str] | None:
        """Validate inputs and return CLI args, or None on validation error."""
        password = self.inp_password.text().strip()
        if not password:
            QMessageBox.warning(self, "Missing field", "Password is required.")
            return None

        args = [
            "setup",
            "--username", self.inp_username.text().strip() or "admin",
            "--password", password,
        ]
        if email := self.inp_email.text().strip():
            args += ["--email", email]
        args += ["--port", str(self.inp_port.value())]
        if domain := self.inp_domain.text().strip():
            args += ["--domain", domain]
        if self.chk_actions.isChecked():
            args += ["--actions"]
        return args

    def current_port(self) -> int:
        return self.inp_port.value()

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        inner = QWidget()
        lay   = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        lay.addWidget(self._make_credentials_group())
        lay.addWidget(self._make_server_group())
        lay.addWidget(self._make_ini_editor_group())
        lay.addLayout(self._make_action_row())
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        outer.addWidget(scroll)

    def _make_credentials_group(self) -> QGroupBox:
        grp = QGroupBox("Admin credentials")
        lay = QVBoxLayout(grp)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Username"))
        self.inp_username = QLineEdit("admin")
        row1.addWidget(self.inp_username)
        row1.addWidget(QLabel("Password"))
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.setPlaceholderText("required")
        row1.addWidget(self.inp_password)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Email"))
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("admin@example.com")
        row2.addWidget(self.inp_email)
        lay.addLayout(row2)

        return grp

    def _make_server_group(self) -> QGroupBox:
        grp = QGroupBox("Server")
        lay = QVBoxLayout(grp)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Port"))
        self.inp_port = QSpinBox()
        self.inp_port.setRange(1024, 65535)
        self.inp_port.setValue(3000)
        self.inp_port.setFixedWidth(130)
        row3.addWidget(self.inp_port)
        row3.addSpacing(20)
        row3.addWidget(QLabel("Domain"))
        self.inp_domain = QLineEdit()
        self.inp_domain.setPlaceholderText("localhost  (optional)")
        row3.addWidget(self.inp_domain)
        lay.addLayout(row3)

        actions_row = QHBoxLayout()
        self.chk_actions = QCheckBox("Enable Forgejo Actions (CI/CD) + local artifact storage")
        self.chk_actions.setToolTip(
            "Adds [actions] ENABLED=true and [actions.artifacts] STORAGE_TYPE=local "
            "+ PATH to app.ini, so workflow artifact uploads work with self-hosted runners."
        )
        actions_row.addWidget(self.chk_actions, stretch=1)

        self.btn_actions_apply = QPushButton("Apply Now")
        self.btn_actions_apply.setToolTip(
            "Apply [actions] settings to the existing app.ini immediately, "
            "without re-running setup (use this if Forgejo is already configured)."
        )
        actions_row.addWidget(self.btn_actions_apply)
        lay.addLayout(actions_row)

        return grp

    def _make_ini_editor_group(self) -> QGroupBox:
        grp  = QGroupBox("app.ini Editor")
        lay  = QVBoxLayout(grp)
        lay.setSpacing(8)

        hint = QLabel(
            "💡 Open the full app.ini in a text editor with syntax highlighting "
            "and inline warnings. Restart Forgejo afterwards for changes to take effect."
        )
        hint.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.btn_cfg_edit = QPushButton("📝  Edit app.ini")
        self.btn_cfg_edit.setFixedHeight(48)
        lay.addWidget(self.btn_cfg_edit)

        return grp

    def _make_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.btn_setup = QPushButton("⚙  Run Setup")
        self.btn_setup.setObjectName("btn_setup")
        self.btn_setup.setFixedHeight(52)
        row.addStretch()
        row.addWidget(self.btn_setup)
        return row
