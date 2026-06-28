# gui/tabs/runner.py
"""Runner tab — install, register, and control the forgejo-runner / act_runner daemon."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from forge.constants import BG_SURFACE, FG_SUBTLE, GREEN, MAUVE, RED, TEAL


class RunnerTab(QWidget):
    """🏃 Runner tab widget.

    Exposes individual button widgets so MainWindow can connect slots.
    Call ``set_status_label()`` to update the coloured badge.
    ``get_register_args()`` returns validated CLI args for registration.
    ``get_runner_path_override()`` returns the pinned runner binary path (or '').
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── public interface ──────────────────────────────────────────────

    def set_status_label(self, text: str, color: str):
        self.lbl_runner_status.setText(text)
        self.lbl_runner_status.setStyleSheet(
            f"color: {color}; background: {BG_SURFACE}; font-weight: bold; "
            f"padding: 3px 8px; border-radius: 4px;"
        )

    def get_runner_path_override(self) -> str:
        return self.inp_runner_bin_path.text().strip()

    def set_runner_path_field(self, path: str):
        if not self.inp_runner_bin_path.text():
            self.inp_runner_bin_path.setText(path)

    def get_register_args(self) -> list[str] | None:
        url   = self.inp_runner_url.text().strip()
        token = self.inp_runner_token.text().strip()
        if not url or not token:
            QMessageBox.warning(
                self, "Missing fields",
                "Instance URL and Token are both required.",
            )
            return None

        args = ["register", "--url", url, "--token", token]
        if uuid  := self.inp_runner_uuid.text().strip():
            args += ["--uuid", uuid]
        if name  := self.inp_runner_name.text().strip():
            args += ["--name", name]
        if labels := self.inp_runner_labels.text().strip():
            args += ["--labels", labels]
        if self.chk_runner_clean.isChecked():
            args += ["--clean"]
        return args

    def set_buttons_enabled(self, enabled: bool):
        for name in (
            "btn_runner_install", "btn_runner_uninstall",
            "btn_runner_register", "btn_runner_start",
            "btn_runner_stop", "btn_runner_status_btn",
        ):
            if widget := getattr(self, name, None):
                widget.setEnabled(enabled)

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        lay   = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        lay.addLayout(self._make_status_row())
        lay.addWidget(self._make_path_group())
        lay.addWidget(self._make_install_group())
        lay.addWidget(self._make_register_group())
        lay.addWidget(self._make_control_group())
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        outer.addWidget(scroll)

    def _make_status_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        lbl = QLabel("Runner status:")
        lbl.setStyleSheet(f"color: {FG_SUBTLE};")

        self.lbl_runner_status = QLabel("● Unknown")
        self.lbl_runner_status.setStyleSheet(
            f"color: {FG_SUBTLE}; background: {BG_SURFACE}; font-weight: bold; "
            f"padding: 3px 8px; border-radius: 4px;"
        )

        self.btn_runner_refresh = QPushButton("⟳ Refresh")
        self.btn_runner_refresh.setFixedHeight(36)

        row.addWidget(lbl)
        row.addWidget(self.lbl_runner_status)
        row.addStretch()
        row.addWidget(self.btn_runner_refresh)
        return row

    def _make_path_group(self) -> QGroupBox:
        grp = QGroupBox("Runner Binary Path")
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)

        path_row = QHBoxLayout()
        self.inp_runner_bin_path = QLineEdit()
        self.inp_runner_bin_path.setPlaceholderText(
            "/usr/local/bin/forgejo-runner   (leave empty = auto-detect from PATH)"
        )
        path_row.addWidget(self.inp_runner_bin_path, stretch=1)

        self.btn_runner_bin_auto = QPushButton("Auto")
        self.btn_runner_bin_auto.setFixedWidth(90)
        self.btn_runner_bin_auto.setFixedHeight(44)
        path_row.addWidget(self.btn_runner_bin_auto)

        self.btn_runner_bin_set = QPushButton("Set Path")
        self.btn_runner_bin_set.setFixedHeight(44)
        path_row.addWidget(self.btn_runner_bin_set)

        lay.addLayout(path_row)

        hint = QLabel(
            "💡 'Auto' scans PATH → ~/.local/bin → /usr/local/bin for forgejo-runner / act_runner\n"
            "   'Set Path' pins whatever you type above for this session"
        )
        hint.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        lay.addWidget(hint)

        return grp

    def _make_install_group(self) -> QGroupBox:
        grp = QGroupBox("Install / Update Runner Binary")
        lay = QVBoxLayout(grp)
        lay.setSpacing(8)

        note = QLabel(
            "Linux → forgejo-runner (code.forgejo.org)    |    Windows / macOS → gitea-runner (gitea.com)"
        )
        note.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        lay.addWidget(note)

        row = QHBoxLayout()

        self.btn_runner_install = QPushButton("⬇  Install Runner")
        self.btn_runner_install.setObjectName("btn_runner_install")
        self.btn_runner_install.setFixedHeight(48)
        row.addWidget(self.btn_runner_install)

        row.addStretch()

        self.btn_runner_uninstall = QPushButton("🗑  Uninstall Runner")
        self.btn_runner_uninstall.setObjectName("btn_runner_uninstall")
        self.btn_runner_uninstall.setFixedHeight(48)
        row.addWidget(self.btn_runner_uninstall)

        lay.addLayout(row)
        return grp

    def _make_register_group(self) -> QGroupBox:
        grp = QGroupBox("Register Runner")
        lay = QVBoxLayout(grp)
        lay.setSpacing(8)

        def _field(label: str, placeholder: str, pw: bool = False) -> QLineEdit:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(115)
            lbl.setStyleSheet(f"color: {FG_SUBTLE};")
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            if pw:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            row.addWidget(lbl)
            row.addWidget(inp, stretch=1)
            lay.addLayout(row)
            return inp

        self.inp_runner_url    = _field("Instance URL", "http://localhost:3000")
        self.inp_runner_token  = _field("Token", "Paste runner registration token here", pw=True)
        self.inp_runner_uuid   = _field("UUID", "UUID shown on Forgejo's 'Set up runner' page")
        self.inp_runner_name   = _field("Runner name", "my-runner  (leave blank for hostname)")
        self.inp_runner_labels = _field("Labels", "ubuntu-latest:host")
        self.inp_runner_labels.setText("ubuntu-latest:host")

        hint = QLabel(
            "💡 Copy the UUID + Token together from Forgejo: Settings → Actions → Runners → "
            "Create new runner ('Set up runner' page)"
        )
        hint.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        lay.addWidget(hint)

        self.chk_runner_clean = QCheckBox(
            "Clean register (discard previous config.yml + .runner state)"
        )
        lay.addWidget(self.chk_runner_clean)

        self.btn_runner_register = QPushButton("🔗  Register Runner")
        self.btn_runner_register.setObjectName("btn_runner_register")
        self.btn_runner_register.setFixedHeight(48)
        lay.addWidget(self.btn_runner_register)

        return grp

    def _make_control_group(self) -> QGroupBox:
        grp = QGroupBox("Runner Daemon Control")
        lay = QHBoxLayout(grp)
        lay.setSpacing(10)

        self.btn_runner_start = QPushButton("▶  Start")
        self.btn_runner_start.setObjectName("btn_runner_start")
        self.btn_runner_start.setFixedHeight(48)

        self.btn_runner_stop = QPushButton("⏹  Stop")
        self.btn_runner_stop.setObjectName("btn_runner_stop")
        self.btn_runner_stop.setFixedHeight(48)

        self.btn_runner_status_btn = QPushButton("ℹ  Status")
        self.btn_runner_status_btn.setObjectName("btn_runner_status")
        self.btn_runner_status_btn.setFixedHeight(48)

        lay.addWidget(self.btn_runner_start)
        lay.addWidget(self.btn_runner_stop)
        lay.addStretch()
        lay.addWidget(self.btn_runner_status_btn)

        return grp
