# gui/tabs/email.py
"""Email / Mailer tab — configure SMTP settings for Forgejo."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from forge.constants import FG_SUBTLE


class EmailTab(QWidget):
    """📧 Email tab widget.

    Owns SMTP configuration fields and exposes ``get_email_args()``
    for MainWindow to pass to the CLI worker.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── public interface ──────────────────────────────────────────────

    def get_email_args(self) -> list[str] | None:
        """Validate inputs and return CLI args, or None on validation error."""
        mail_from = self.inp_mail_from.text().strip()
        smtp_addr = self.inp_mail_addr.text().strip()
        smtp_port = str(self.inp_mail_port.value())
        protocol  = "smtps" if self.cmb_mail_proto.currentIndex() == 0 else "smtp"
        user      = self.inp_mail_user.text().strip()
        passwd    = self.inp_mail_passwd.text()

        if not mail_from or not user or not passwd:
            QMessageBox.warning(
                self, "Missing fields",
                "FROM address, User, and Password are all required.",
            )
            return None

        return [
            "email-setup",
            "--from",      mail_from,
            "--smtp-addr", smtp_addr,
            "--smtp-port", smtp_port,
            "--protocol",  protocol,
            "--user",      user,
            "--passwd",    passwd,
        ]

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        lay   = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        lay.addWidget(self._make_sender_group())
        lay.addWidget(self._make_smtp_group())
        lay.addWidget(self._make_creds_group())
        lay.addWidget(self._make_help_note())
        lay.addLayout(self._make_action_row())
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        outer.addWidget(scroll)

    def _make_sender_group(self) -> QGroupBox:
        grp = QGroupBox("Sender identity")
        lay = QVBoxLayout(grp)

        row = QHBoxLayout()
        row.addWidget(QLabel("FROM address"))
        self.inp_mail_from = QLineEdit()
        self.inp_mail_from.setPlaceholderText("forgejo@yourdomain.com")
        row.addWidget(self.inp_mail_from)
        lay.addLayout(row)

        return grp

    def _make_smtp_group(self) -> QGroupBox:
        grp = QGroupBox("SMTP server")
        lay = QVBoxLayout(grp)

        row_addr = QHBoxLayout()
        row_addr.addWidget(QLabel("SMTP host"))
        self.inp_mail_addr = QLineEdit("smtp.gmail.com")
        row_addr.addWidget(self.inp_mail_addr)
        row_addr.addSpacing(16)
        row_addr.addWidget(QLabel("Port"))
        self.inp_mail_port = QSpinBox()
        self.inp_mail_port.setRange(1, 65535)
        self.inp_mail_port.setValue(465)
        self.inp_mail_port.setFixedWidth(110)
        row_addr.addWidget(self.inp_mail_port)
        lay.addLayout(row_addr)

        row_proto = QHBoxLayout()
        row_proto.addWidget(QLabel("Protocol"))
        self.cmb_mail_proto = QComboBox()
        self.cmb_mail_proto.addItems([
            "smtps  (SSL/TLS — port 465)",
            "smtp  (STARTTLS — port 587)",
        ])
        self.cmb_mail_proto.currentIndexChanged.connect(self._on_proto_changed)
        row_proto.addWidget(self.cmb_mail_proto)
        row_proto.addStretch()
        lay.addLayout(row_proto)

        return grp

    def _make_creds_group(self) -> QGroupBox:
        grp = QGroupBox("SMTP credentials")
        lay = QVBoxLayout(grp)

        row_user = QHBoxLayout()
        row_user.addWidget(QLabel("User (email)"))
        self.inp_mail_user = QLineEdit()
        self.inp_mail_user.setPlaceholderText("yourname@gmail.com")
        row_user.addWidget(self.inp_mail_user)
        lay.addLayout(row_user)

        row_pass = QHBoxLayout()
        row_pass.addWidget(QLabel("Password"))
        self.inp_mail_passwd = QLineEdit()
        self.inp_mail_passwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_mail_passwd.setPlaceholderText(
            "App Password (Gmail 2FA) or SMTP password"
        )
        row_pass.addWidget(self.inp_mail_passwd)
        lay.addLayout(row_pass)

        return grp

    def _make_help_note(self) -> QLabel:
        note = QLabel(
            "💡 Gmail: enable 2FA → create an App Password at myaccount.google.com/apppasswords\n"
            "   Free alternatives: Brevo (brevo.com), Mailgun, Cloudflare Email Routing"
        )
        note.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        note.setWordWrap(True)
        return note

    def _make_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.btn_email_apply = QPushButton("📧  Apply Mailer Config")
        self.btn_email_apply.setObjectName("btn_email_apply")
        self.btn_email_apply.setFixedHeight(52)

        self.btn_restart = QPushButton("🔄  Restart Now")
        self.btn_restart.setFixedHeight(52)
        self.btn_restart.setMinimumWidth(200)

        row.addStretch()
        row.addWidget(self.btn_email_apply)
        row.addWidget(self.btn_restart)
        return row

    # ── slots ─────────────────────────────────────────────────────────

    def _on_proto_changed(self, index: int):
        self.inp_mail_port.setValue(465 if index == 0 else 587)
