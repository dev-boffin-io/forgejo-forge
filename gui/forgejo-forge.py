#!/usr/bin/env python3
"""
forgejo-forge GUI
PyQt6 frontend for the forgejo-forge CLI binary.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QSpinBox,
    QTabWidget, QFrame, QSizePolicy, QMessageBox, QCheckBox, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QProcess
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor

# ── ANSI strip ────────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mABCDEFGHJKSTfhilmnqrsu]')

def strip_ansi(text: str) -> str:
    """Remove ANSI terminal escape sequences from text.

    forgejo-main (installer) emits coloured output via ANSI codes which
    look like garbage inside a Qt widget.  Strip them before display.
    """
    return _ANSI_RE.sub('', text)


# ── Constants ────────────────────────────────────────────────────────────────

APP_NAME    = "forgejo-forge"
APP_VERSION = "1.0.0"
BINARY_NAME = "forgejo-forge"

# Catppuccin Mocha
BG_BASE    = "#1e1e2e"
BG_MANTLE  = "#181825"
BG_CRUST   = "#11111b"
BG_SURFACE = "#313244"
BG_OVERLAY = "#45475a"
FG_TEXT    = "#cdd6f4"
FG_SUBTLE  = "#a6adc8"
ACCENT     = "#89b4fa"   # blue
GREEN      = "#a6e3a1"
RED        = "#f38ba8"
YELLOW     = "#f9e2af"
MAUVE      = "#cba6f7"
TEAL       = "#94e2d5"
PEACH      = "#fab387"

STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {FG_TEXT};
    font-family: 'JetBrains Mono', 'Fira Code', 'Monospace';
    font-size: 20px;
}}
QGroupBox {{
    border: 1px solid {BG_OVERLAY};
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 12px;
    color: {ACCENT};
    font-weight: bold;
    font-size: 18px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
QLineEdit, QSpinBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {BG_OVERLAY};
    border-radius: 4px;
    padding: 10px 12px;
    color: {FG_TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {BG_OVERLAY};
    border: none;
    width: 16px;
}}
QPushButton {{
    background-color: {BG_SURFACE};
    border: 1px solid {BG_OVERLAY};
    border-radius: 4px;
    padding: 10px 22px;
    color: {FG_TEXT};
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {BG_OVERLAY};
    border: 1px solid {ACCENT};
}}
QPushButton:pressed {{
    background-color: {ACCENT};
    color: {BG_BASE};
}}
QPushButton:disabled {{
    color: {BG_OVERLAY};
    border-color: {BG_SURFACE};
}}
QPushButton#btn_setup    {{ border-color: {MAUVE}; color: {MAUVE}; }}
QPushButton#btn_setup:hover {{ background-color: {MAUVE}; color: {BG_BASE}; }}
QPushButton#btn_start    {{ border-color: {GREEN}; color: {GREEN}; }}
QPushButton#btn_start:hover {{ background-color: {GREEN}; color: {BG_BASE}; }}
QPushButton#btn_stop     {{ border-color: {RED}; color: {RED}; }}
QPushButton#btn_stop:hover {{ background-color: {RED}; color: {BG_BASE}; }}
QPushButton#btn_restart  {{ border-color: {YELLOW}; color: {YELLOW}; }}
QPushButton#btn_restart:hover {{ background-color: {YELLOW}; color: {BG_BASE}; }}
QPushButton#btn_logs     {{ border-color: {TEAL}; color: {TEAL}; }}
QPushButton#btn_logs:hover {{ background-color: {TEAL}; color: {BG_BASE}; }}
QPushButton#btn_uninstall {{ border-color: {RED}; color: {RED}; }}
QPushButton#btn_uninstall:hover {{ background-color: {RED}; color: {BG_BASE}; }}
QPushButton#btn_bin_install {{ border-color: {GREEN}; color: {GREEN}; }}
QPushButton#btn_bin_install:hover {{ background-color: {GREEN}; color: {BG_BASE}; }}
QPushButton#btn_bin_update {{ border-color: {PEACH}; color: {PEACH}; }}
QPushButton#btn_bin_update:hover {{ background-color: {PEACH}; color: {BG_BASE}; }}
QPushButton#btn_bin_check {{ border-color: {TEAL}; color: {TEAL}; }}
QPushButton#btn_bin_check:hover {{ background-color: {TEAL}; color: {BG_BASE}; }}
QTextEdit {{
    background-color: {BG_MANTLE};
    border: 1px solid {BG_OVERLAY};
    border-radius: 4px;
    padding: 6px;
    color: {FG_TEXT};
    font-family: 'JetBrains Mono', 'Fira Code', 'Monospace';
    font-size: 19px;
}}
QTabWidget::pane {{
    border: 1px solid {BG_OVERLAY};
    border-radius: 4px;
    background: {BG_BASE};
}}
QTabBar::tab {{
    background: {BG_MANTLE};
    color: {FG_SUBTLE};
    padding: 10px 24px;
    border: 1px solid {BG_OVERLAY};
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {BG_SURFACE};
    color: {ACCENT};
    border-color: {ACCENT};
}}
QLabel#status_label {{
    font-size: 19px;
    padding: 3px 8px;
    border-radius: 4px;
}}
QCheckBox {{
    spacing: 6px;
    color: {FG_TEXT};
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid {BG_OVERLAY};
    background: {BG_SURFACE};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QFrame#divider {{
    color: {BG_OVERLAY};
}}
"""

# ── Worker thread ─────────────────────────────────────────────────────────────

class CommandWorker(QThread):
    """Runs a forgejo-forge subcommand in a background thread."""
    output_line = pyqtSignal(str)
    finished    = pyqtSignal(int)   # exit code

    def __init__(self, args: list[str], binary_override: str = "", parent=None):
        super().__init__(parent)
        self.args = args
        self.binary_override = binary_override

    def run(self):
        binary = find_binary(self.binary_override)
        if not binary:
            self.output_line.emit("❌ forgejo-forge binary not found in PATH or ./bin/")
            self.finished.emit(1)
            return

        cmd = [binary] + self.args
        self.output_line.emit(f"$ {' '.join(cmd)}\n")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in proc.stdout:
                self.output_line.emit(line.rstrip())
            proc.wait()
            self.finished.emit(proc.returncode)
        except Exception as e:
            self.output_line.emit(f"❌ {e}")
            self.finished.emit(1)


class InstallerWorker(QThread):
    """Runs forgejo-main (the installer) in a background thread."""
    output_line = pyqtSignal(str)
    finished    = pyqtSignal(int)

    def __init__(self, args: list[str], parent=None):
        super().__init__(parent)
        self.args = args

    def run(self):
        binary = find_installer_binary()
        if not binary:
            self.output_line.emit("❌ forgejo-main installer binary not found in PATH or ./bin/")
            self.finished.emit(1)
            return

        cmd = [binary] + self.args
        self.output_line.emit(f"$ {' '.join(cmd)}\n")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in proc.stdout:
                self.output_line.emit(strip_ansi(line.rstrip()))
            proc.wait()
            self.finished.emit(proc.returncode)
        except Exception as e:
            self.output_line.emit(f"❌ {e}")
            self.finished.emit(1)


class LogFollowWorker(QThread):
    """Follows gitea logs (blocking tail -f or journalctl -f)."""
    output_line = pyqtSignal(str)
    finished    = pyqtSignal(int)

    def __init__(self, args: list[str], binary_override: str = "", parent=None):
        super().__init__(parent)
        self.args = args
        self.binary_override = binary_override
        self._proc = None

    def run(self):
        binary = find_binary(self.binary_override)
        if not binary:
            self.output_line.emit("❌ forgejo-forge binary not found")
            self.finished.emit(1)
            return

        cmd = [binary] + self.args
        self.output_line.emit(f"$ {' '.join(cmd)}\n")

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in self._proc.stdout:
                self.output_line.emit(line.rstrip())
            self._proc.wait()
            self.finished.emit(self._proc.returncode)
        except Exception as e:
            self.output_line.emit(f"❌ {e}")
            self.finished.emit(1)

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class BinaryCheckWorker(QThread):
    """Detects installed forgejo/gitea binary and fetches latest release version."""
    result = pyqtSignal(dict)   # {binary, path, installed, latest, source, up_to_date}
    error  = pyqtSignal(str)

    SEMVER_RE = re.compile(r'\d+\.\d+\.\d+')
    FORGEJO_API = "https://codeberg.org/api/v1/repos/forgejo/forgejo/releases/latest"
    GITEA_API   = "https://api.github.com/repos/go-gitea/gitea/releases/latest"

    def __init__(self, custom_path: str = "", parent=None):
        super().__init__(parent)
        self.custom_path = custom_path.strip()

    def run(self):
        # 1. Locate the binary
        binary_path = ""
        binary_name = ""

        if self.custom_path and os.path.isfile(self.custom_path) and os.access(self.custom_path, os.X_OK):
            binary_path = self.custom_path
            base = os.path.basename(self.custom_path).lower().replace(".exe", "")
            binary_name = "gitea" if "gitea" in base else "forgejo"
        else:
            for name in ("forgejo", "gitea"):
                p = shutil.which(name)
                if p:
                    binary_path = p
                    binary_name = name
                    break

        if not binary_path:
            # Also scan common install locations
            common = [
                "/usr/local/bin/forgejo", "/usr/local/bin/gitea",
                os.path.expanduser("~/.local/bin/forgejo"),
                os.path.expanduser("~/.local/bin/gitea"),
            ]
            for candidate in common:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    binary_path = candidate
                    binary_name = "gitea" if "gitea" in candidate else "forgejo"
                    break

        if not binary_path:
            self.error.emit("forgejo / gitea not found in PATH or common locations")
            return

        # 2. Get installed version
        installed = "unknown"
        try:
            out = subprocess.run(
                [binary_path, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            m = self.SEMVER_RE.search(out.stdout + out.stderr)
            if m:
                installed = m.group()
        except Exception:
            pass

        # 3. Fetch latest release from upstream API
        source = "gitea" if binary_name == "gitea" else "forgejo"
        latest = self._fetch_latest(source)

        up_to_date = (installed != "unknown" and installed == latest)

        self.result.emit({
            "binary":     binary_name,
            "path":       binary_path,
            "installed":  installed,
            "latest":     latest,
            "source":     source,
            "up_to_date": up_to_date,
        })

    def _fetch_latest(self, source: str) -> str:
        try:
            url = self.GITEA_API if source == "gitea" else self.FORGEJO_API
            req = urllib.request.Request(url, headers={
                "User-Agent": "forgejo-installer/1.0",
                "Accept":     "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                tag = data.get("tag_name", "")
                m = self.SEMVER_RE.search(tag)
                return m.group() if m else "unknown"
        except Exception as e:
            return f"fetch failed ({e})"


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_binary(override: str = "") -> str | None:
    """Locate forgejo-forge binary.

    If *override* is given (set via the Binary tab's path field) that path
    is returned directly after existence + executable checks — no further
    search is done.

    Auto-search order:
    1. PATH  (works after 'make install')
    2. Same directory as this executable  (frozen PyInstaller build:
       both forgejo-forge and forgejo-forge-gui live in bin/)
    3. ./bin/ relative to CWD  (running from source: python3 gui/forgejo-forge.py)
    4. ../bin/ relative to script location
    """
    # 0. Manual override from Binary tab
    if override and os.path.isfile(override) and os.access(override, os.X_OK):
        return override

    # 1. PATH
    if path := shutil.which(BINARY_NAME):
        return path

    # 2. Same dir as the running executable (frozen or not)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidate = os.path.join(exe_dir, BINARY_NAME)
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate

    # 3-4. Relative paths from CWD / script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for base in [os.getcwd(), script_dir, os.path.join(script_dir, "..")]:
        candidate = os.path.join(base, "bin", BINARY_NAME)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def find_installer_binary() -> str | None:
    """Locate the forgejo-main installer binary.

    Search order: PATH → same dir as exe → ./bin/ → ../bin/
    Tries both 'forgejo-main' and platform-specific suffixed variants.
    """
    import platform
    machine = platform.machine().lower()
    arch_suffix = "arm64" if machine in ("aarch64", "arm64") else "amd64"
    is_win = sys.platform == "win32"
    os_tag  = "windows" if is_win else "linux"
    exe_ext = ".exe" if is_win else ""

    candidates_names = [
        f"forgejo-main{exe_ext}",
        f"forgejo-main-{os_tag}-{arch_suffix}{exe_ext}",
        f"forgejo-main-{arch_suffix}{exe_ext}",
    ]

    # 1. PATH
    for name in candidates_names:
        if path := shutil.which(name):
            return path

    # 2. Same dir as running executable
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for name in candidates_names:
        candidate = os.path.join(exe_dir, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 3-4. bin/ relative to CWD / script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for base in [os.getcwd(), script_dir, os.path.join(script_dir, "..")]:
        for name in candidates_names:
            candidate = os.path.join(base, "bin", name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

    return None


def screen_aware_size(app: QApplication) -> tuple[int, int]:
    screen = app.primaryScreen().availableGeometry()
    w = min(1100, int(screen.width()  * 0.88))
    h = min(800, int(screen.height() * 0.88))
    return w, h


# ── Main window ───────────────────────────────────────────────────────────────

class ForgejoForgeGUI(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        w, h = screen_aware_size(app)
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(w, h)
        self.setStyleSheet(STYLE)

        self._worker: CommandWorker | None = None
        self._log_worker: LogFollowWorker | None = None
        self._bin_check_worker: BinaryCheckWorker | None = None
        self._log_buffer: list[str] = []
        self._custom_forgejo_path: str = ""

        # Drains _log_buffer → log_view every 100 ms
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(100)
        self._log_timer.timeout.connect(self._flush_log_buffer)

        self._build_ui()
        self._check_binary()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Header
        root.addWidget(self._make_header())

        # Status bar
        self.status_label = QLabel("● Unknown")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self.status_label)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._make_setup_tab(),   "⚙  Setup")
        tabs.addTab(self._make_control_tab(), "▶  Control")
        tabs.addTab(self._make_email_tab(),   "📧  Email")
        tabs.addTab(self._make_logs_tab(),    "📄  Logs")
        tabs.addTab(self._make_binary_tab(),  "🔧  Binary")
        root.addWidget(tabs, stretch=1)

        # Output console
        root.addWidget(self._make_console())

        # Status timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(5000)
        self._refresh_status()

    def _make_header(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        title = QLabel(f"🦊  {APP_NAME}")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {ACCENT};")

        binary = find_binary(self._custom_forgejo_path) or "not found"
        sub = QLabel(f"binary: {binary}")
        sub.setStyleSheet(f"font-size: 18px; color: {FG_SUBTLE};")

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(sub)
        return w

    # ── Setup tab ─────────────────────────────────────────────────────

    def _make_setup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # Credentials
        creds = QGroupBox("Admin credentials")
        cg = QVBoxLayout(creds)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Username"))
        self.inp_username = QLineEdit("admin")
        row1.addWidget(self.inp_username)
        row1.addWidget(QLabel("Password"))
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.setPlaceholderText("required")
        row1.addWidget(self.inp_password)
        cg.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Email"))
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("admin@example.com")
        row2.addWidget(self.inp_email)
        cg.addLayout(row2)

        lay.addWidget(creds)

        # Server
        srv = QGroupBox("Server")
        sg = QVBoxLayout(srv)

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
        sg.addLayout(row3)

        lay.addWidget(srv)

        # Action
        btn_row = QHBoxLayout()
        self.btn_setup = QPushButton("⚙  Run Setup")
        self.btn_setup.setObjectName("btn_setup")
        self.btn_setup.setFixedHeight(52)
        self.btn_setup.clicked.connect(self._run_setup)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_setup)
        lay.addLayout(btn_row)

        lay.addStretch()
        return w

    # ── Control tab ───────────────────────────────────────────────────

    def _make_control_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        grp = QGroupBox("Service control")
        gg = QHBoxLayout(grp)
        gg.setSpacing(10)

        btns = [
            ("btn_start",   "▶  Start",   self._run_start),
            ("btn_stop",    "■  Stop",    self._run_stop),
            ("btn_restart", "↺  Restart", self._run_restart),
        ]
        for name, label, slot in btns:
            b = QPushButton(label)
            b.setObjectName(name)
            b.setFixedHeight(52)
            b.clicked.connect(slot)
            gg.addWidget(b)
            setattr(self, name, b)

        lay.addWidget(grp)

        # Status display
        info = QGroupBox("Instance info")
        il = QVBoxLayout(info)
        self.info_text = QLabel("Run 'status' or wait for auto-refresh.")
        self.info_text.setStyleSheet(f"color: {FG_SUBTLE}; font-size: 19px;")
        self.info_text.setWordWrap(True)
        il.addWidget(self.info_text)

        btn_status = QPushButton("⟳  Refresh status")
        btn_status.clicked.connect(self._refresh_status)
        il.addWidget(btn_status)
        lay.addWidget(info)

        # Uninstall
        danger = QGroupBox("Danger zone")
        dl = QVBoxLayout(danger)
        danger.setStyleSheet(f"QGroupBox {{ border-color: {RED}; color: {RED}; }}")
        self.btn_uninstall = QPushButton("🗑  Uninstall Forgejo")
        self.btn_uninstall.setObjectName("btn_uninstall")
        self.btn_uninstall.setFixedHeight(52)
        self.btn_uninstall.clicked.connect(self._run_uninstall)
        dl.addWidget(self.btn_uninstall)
        lay.addWidget(danger)

        lay.addStretch()
        return w

    # ── Email / Mailer tab ────────────────────────────────────────────

    def _make_email_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        # ── Sender ────────────────────────────────────────────────────
        grp_sender = QGroupBox("Sender identity")
        sg = QVBoxLayout(grp_sender)

        row_from = QHBoxLayout()
        row_from.addWidget(QLabel("FROM address"))
        self.inp_mail_from = QLineEdit()
        self.inp_mail_from.setPlaceholderText("forgejo@yourdomain.com")
        row_from.addWidget(self.inp_mail_from)
        sg.addLayout(row_from)

        lay.addWidget(grp_sender)

        # ── SMTP server ───────────────────────────────────────────────
        grp_smtp = QGroupBox("SMTP server")
        smg = QVBoxLayout(grp_smtp)

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
        smg.addLayout(row_addr)

        row_proto = QHBoxLayout()
        row_proto.addWidget(QLabel("Protocol"))
        self.cmb_mail_proto = QComboBox()
        self.cmb_mail_proto.addItems(["smtps  (SSL/TLS — port 465)", "smtp  (STARTTLS — port 587)"])
        self.cmb_mail_proto.currentIndexChanged.connect(self._mail_proto_changed)
        row_proto.addWidget(self.cmb_mail_proto)
        row_proto.addStretch()
        smg.addLayout(row_proto)

        lay.addWidget(grp_smtp)

        # ── Credentials ───────────────────────────────────────────────
        grp_creds = QGroupBox("SMTP credentials")
        cg = QVBoxLayout(grp_creds)

        row_user = QHBoxLayout()
        row_user.addWidget(QLabel("User (email)"))
        self.inp_mail_user = QLineEdit()
        self.inp_mail_user.setPlaceholderText("yourname@gmail.com")
        row_user.addWidget(self.inp_mail_user)
        cg.addLayout(row_user)

        row_pass = QHBoxLayout()
        row_pass.addWidget(QLabel("Password"))
        self.inp_mail_passwd = QLineEdit()
        self.inp_mail_passwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_mail_passwd.setPlaceholderText("App Password (Gmail 2FA) or SMTP password")
        row_pass.addWidget(self.inp_mail_passwd)
        cg.addLayout(row_pass)

        lay.addWidget(grp_creds)

        # ── Help note ─────────────────────────────────────────────────
        note = QLabel(
            "💡 Gmail: enable 2FA → create an App Password at myaccount.google.com/apppasswords\n"
            "   Free alternatives: Brevo (brevo.com), Mailgun, Cloudflare Email Routing"
        )
        note.setStyleSheet(f"font-size: 15px; color: {FG_SUBTLE};")
        note.setWordWrap(True)
        lay.addWidget(note)

        # ── Actions ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.btn_email_apply = QPushButton("📧  Apply Mailer Config")
        self.btn_email_apply.setObjectName("btn_email_apply")
        self.btn_email_apply.setFixedHeight(52)
        self.btn_email_apply.clicked.connect(self._run_email_setup)

        btn_restart = QPushButton("🔄  Restart Now")
        btn_restart.setFixedHeight(52)
        btn_restart.setMinimumWidth(200)
        btn_restart.clicked.connect(self._run_restart)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_email_apply)
        btn_row.addWidget(btn_restart)
        lay.addLayout(btn_row)

        lay.addStretch()
        return w

    def _mail_proto_changed(self, index: int):
        self.inp_mail_port.setValue(465 if index == 0 else 587)

    def _run_email_setup(self):
        mail_from   = self.inp_mail_from.text().strip()
        smtp_addr   = self.inp_mail_addr.text().strip()
        smtp_port   = str(self.inp_mail_port.value())
        proto_index = self.cmb_mail_proto.currentIndex()
        protocol    = "smtps" if proto_index == 0 else "smtp"
        user        = self.inp_mail_user.text().strip()
        passwd      = self.inp_mail_passwd.text()

        if not mail_from or not user or not passwd:
            QMessageBox.warning(self, "Missing fields",
                                "FROM address, User, and Password are all required.")
            return

        self._run_command([
            "email-setup",
            "--from",      mail_from,
            "--smtp-addr", smtp_addr,
            "--smtp-port", smtp_port,
            "--protocol",  protocol,
            "--user",      user,
            "--passwd",    passwd,
        ])

    # ── Logs tab ──────────────────────────────────────────────────────

    def _make_logs_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
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
        self.btn_logs.clicked.connect(self._toggle_logs)
        opts.addWidget(self.btn_logs)
        lay.addLayout(opts)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs will appear here...")
        lay.addWidget(self.log_view, stretch=1)
        return w

    # ── Binary tab ────────────────────────────────────────────────────

    def _make_binary_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        # ── Info group ────────────────────────────────────────────────
        grp_info = QGroupBox("Detected binary")
        ig = QVBoxLayout(grp_info)
        ig.setSpacing(8)

        def info_row(label_text: str) -> tuple[QLabel, QLabel]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(110)
            lbl.setStyleSheet(f"color: {FG_SUBTLE};")
            val = QLabel("—")
            val.setStyleSheet(f"color: {FG_TEXT}; font-weight: bold;")
            val.setWordWrap(True)
            row.addWidget(lbl)
            row.addWidget(val, stretch=1)
            ig.addLayout(row)
            return lbl, val

        _, self.lbl_bin_name      = info_row("Binary")
        _, self.lbl_bin_path      = info_row("Path")
        _, self.lbl_bin_installed = info_row("Installed")
        _, self.lbl_bin_latest    = info_row("Latest")

        # Detect button in header row
        detect_row = QHBoxLayout()
        self.btn_bin_detect = QPushButton("⟳  Auto Detect")
        self.btn_bin_detect.setFixedHeight(44)
        self.btn_bin_detect.clicked.connect(self._run_detect_binary)
        detect_row.addStretch()
        detect_row.addWidget(self.btn_bin_detect)
        ig.addLayout(detect_row)

        lay.addWidget(grp_info)

        # ── Path group ────────────────────────────────────────────────
        grp_path = QGroupBox("Path override")
        pg = QVBoxLayout(grp_path)

        path_row = QHBoxLayout()
        self.inp_bin_path = QLineEdit()
        self.inp_bin_path.setPlaceholderText("/usr/local/bin/forgejo  (leave empty for auto)")
        path_row.addWidget(self.inp_bin_path, stretch=1)

        btn_auto = QPushButton("Auto")
        btn_auto.setFixedWidth(80)
        btn_auto.setFixedHeight(44)
        btn_auto.clicked.connect(self._bin_path_auto)
        path_row.addWidget(btn_auto)

        self.btn_bin_set_path = QPushButton("Set Path")
        self.btn_bin_set_path.setFixedHeight(44)
        self.btn_bin_set_path.clicked.connect(self._bin_path_set)
        path_row.addWidget(self.btn_bin_set_path)

        pg.addLayout(path_row)

        note = QLabel(
            "💡 'Auto' scans PATH + /usr/local/bin + ~/.local/bin\n"
            "   'Set Path' uses whatever you type above for this session"
        )
        note.setStyleSheet(f"font-size: 15px; color: {FG_SUBTLE};")
        pg.addWidget(note)

        installer_path = find_installer_binary() or "not found"
        inst_note = QLabel(f"Installer (forgejo-main): {installer_path}")
        inst_note.setStyleSheet(f"font-size: 15px; color: {FG_SUBTLE};")
        pg.addWidget(inst_note)

        lay.addWidget(grp_path)

        # ── Actions group ─────────────────────────────────────────────
        grp_act = QGroupBox("Actions")
        ag = QHBoxLayout(grp_act)
        ag.setSpacing(10)

        self.btn_bin_install = QPushButton("⬇  Install")
        self.btn_bin_install.setObjectName("btn_bin_install")
        self.btn_bin_install.setFixedHeight(52)
        self.btn_bin_install.clicked.connect(self._run_binary_install)

        self.btn_bin_update = QPushButton("⬆  Update")
        self.btn_bin_update.setObjectName("btn_bin_update")
        self.btn_bin_update.setFixedHeight(52)
        self.btn_bin_update.clicked.connect(self._run_binary_update)

        self.btn_bin_check = QPushButton("⟳  Version Check")
        self.btn_bin_check.setObjectName("btn_bin_check")
        self.btn_bin_check.setFixedHeight(52)
        self.btn_bin_check.clicked.connect(self._run_detect_binary)

        ag.addWidget(self.btn_bin_install)
        ag.addWidget(self.btn_bin_update)
        ag.addStretch()
        ag.addWidget(self.btn_bin_check)
        lay.addWidget(grp_act)

        lay.addStretch()

        # Trigger auto-detect on first show
        QTimer.singleShot(500, self._run_detect_binary)

        return w

    # ── Binary tab slots ──────────────────────────────────────────────

    def _run_detect_binary(self):
        """Spawn BinaryCheckWorker to detect installed binary + fetch latest."""
        if self._bin_check_worker and self._bin_check_worker.isRunning():
            return

        self.lbl_bin_name.setText("⏳ detecting…")
        self.lbl_bin_latest.setText("⏳ fetching…")
        self.btn_bin_detect.setEnabled(False)
        self.btn_bin_check.setEnabled(False)

        self._bin_check_worker = BinaryCheckWorker(self._custom_forgejo_path)
        self._bin_check_worker.result.connect(self._on_detect_result)
        self._bin_check_worker.error.connect(self._on_detect_error)
        self._bin_check_worker.finished.connect(
            lambda: (
                self.btn_bin_detect.setEnabled(True),
                self.btn_bin_check.setEnabled(True),
            )
        )
        self._bin_check_worker.start()

    def _on_detect_result(self, data: dict):
        self.lbl_bin_name.setText(data["binary"])
        self.lbl_bin_path.setText(data["path"])

        installed = data["installed"]
        latest    = data["latest"]

        if data.get("up_to_date"):
            self.lbl_bin_installed.setText(f"{installed}  ✔ up to date")
            self.lbl_bin_installed.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
        else:
            self.lbl_bin_installed.setText(installed)
            self.lbl_bin_installed.setStyleSheet(f"color: {FG_TEXT}; font-weight: bold;")

        if "failed" in latest:
            self.lbl_bin_latest.setText(latest)
            self.lbl_bin_latest.setStyleSheet(f"color: {YELLOW}; font-weight: bold;")
        elif installed != "unknown" and installed != latest:
            self.lbl_bin_latest.setText(f"{latest}  ↑ update available")
            self.lbl_bin_latest.setStyleSheet(f"color: {PEACH}; font-weight: bold;")
        else:
            self.lbl_bin_latest.setText(latest)
            self.lbl_bin_latest.setStyleSheet(f"color: {FG_TEXT}; font-weight: bold;")

        # Pre-fill path field if empty
        if not self.inp_bin_path.text():
            self.inp_bin_path.setText(data["path"])

        self._console_write(
            f"✔ Detected: {data['binary']} {installed}  (latest: {latest})",
            color=GREEN,
        )

    def _on_detect_error(self, msg: str):
        self.lbl_bin_name.setText("not found")
        self.lbl_bin_name.setStyleSheet(f"color: {RED}; font-weight: bold;")
        self.lbl_bin_path.setText("—")
        self.lbl_bin_installed.setText("—")
        self.lbl_bin_latest.setText("—")
        self._console_write(f"⚠ {msg}", color=YELLOW)

    def _bin_path_auto(self):
        """Clear custom path override and re-detect."""
        self._custom_forgejo_path = ""
        self.inp_bin_path.clear()
        self._run_detect_binary()

    def _bin_path_set(self):
        """Save manual path and refresh detection."""
        path = self.inp_bin_path.text().strip()
        if path and not (os.path.isfile(path) and os.access(path, os.X_OK)):
            QMessageBox.warning(
                self, "Invalid path",
                f"'{path}' is not an executable file.\nCheck the path and try again.",
            )
            return
        self._custom_forgejo_path = path
        self._run_detect_binary()

    def _run_binary_install(self):
        """Run forgejo-main install."""
        if not find_installer_binary():
            QMessageBox.critical(
                self, "Installer not found",
                "forgejo-main binary not found.\n\nRun 'make installer' to build it first.",
            )
            return
        self._run_installer_command(["install"])

    def _run_binary_update(self):
        """Run forgejo-main update."""
        if not find_installer_binary():
            QMessageBox.critical(
                self, "Installer not found",
                "forgejo-main binary not found.\n\nRun 'make installer' to build it first.",
            )
            return
        self._run_installer_command(["update"])

    def _run_installer_command(self, args: list[str]):
        """Generic runner for forgejo-main sub-commands."""
        if self._worker and self._worker.isRunning():
            self._console_write("⚠ Another command is still running.", color=YELLOW)
            return

        self._set_buttons_enabled(False)
        worker = InstallerWorker(args)
        worker.output_line.connect(self._console_write)
        worker.finished.connect(self._on_installer_finished)
        # Keep a reference so GC doesn't collect the thread
        self._worker = worker  # type: ignore[assignment]
        self._worker.start()

    def _on_installer_finished(self, code: int):
        self._set_buttons_enabled(True)
        if code == 0:
            self._console_write(f"\n✔ Done (exit 0)", color=GREEN)
            # Refresh binary info after install/update
            QTimer.singleShot(800, self._run_detect_binary)
        else:
            self._console_write(f"\n✘ Failed (exit {code})", color=RED)

    # ── Console ───────────────────────────────────────────────────────

    def _make_console(self) -> QGroupBox:
        grp = QGroupBox("Output")
        lay = QVBoxLayout(grp)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(220)
        self.console.setPlaceholderText("Command output will appear here...")
        lay.addWidget(self.console)

        btn_row = QHBoxLayout()
        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(70)
        btn_clear.clicked.connect(self.console.clear)
        btn_row.addStretch()
        btn_row.addWidget(btn_clear)
        lay.addLayout(btn_row)
        return grp

    # ── Binary check ─────────────────────────────────────────────────

    def _check_binary(self):
        if not find_binary(self._custom_forgejo_path):
            self._console_write(
                f"⚠  '{BINARY_NAME}' binary not found.\n"
                f"   Run 'make build' first, or add bin/ to PATH.\n",
                color=YELLOW,
            )

    # ── Command runners ───────────────────────────────────────────────

    def _run_setup(self):
        password = self.inp_password.text().strip()
        if not password:
            QMessageBox.warning(self, "Missing field", "Password is required.")
            return

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

        self._run_command(args)

    def _run_start(self):
        self._run_command(["start"])

    def _run_stop(self):
        self._run_command(["stop"])

    def _run_restart(self):
        self._run_command(["restart"])

    def _run_uninstall(self):
        reply = QMessageBox.question(
            self,
            "Confirm uninstall",
            "This will remove all Forgejo data and configuration.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        binary = find_binary(self._custom_forgejo_path)
        if not binary:
            return
        self._console_write("$ forgejo-forge uninstall\n")
        try:
            result = subprocess.run(
                [binary, "uninstall"],
                input="y\n",
                capture_output=True,
                text=True,
            )
            for line in (result.stdout + result.stderr).splitlines():
                self._console_write(line)
            self._set_status_stopped()
        except Exception as e:
            self._console_write(f"❌ {e}", color=RED)

    def _toggle_logs(self):
        if self._log_worker and self._log_worker.isRunning():
            self._log_timer.stop()
            self._log_worker.stop()
            self._log_worker = None
            self.btn_logs.setText("📄  Show Logs")
            return

        args = ["logs", f"-n{self.inp_lines.value()}"]
        if self.chk_follow.isChecked():
            args.append("-f")

        self.log_view.clear()
        self._log_buffer.clear()

        self._log_worker = LogFollowWorker(args, binary_override=self._custom_forgejo_path)
        self._log_worker.output_line.connect(self._log_buffer.append)
        self._log_worker.finished.connect(self._on_log_finished)
        self._log_worker.start()
        self._log_timer.start()
        self.btn_logs.setText("⏹  Stop Logs")

    # ── Generic command runner ────────────────────────────────────────

    def _run_command(self, args: list[str]):
        if self._worker and self._worker.isRunning():
            self._console_write("⚠ Another command is still running.", color=YELLOW)
            return

        self._set_buttons_enabled(False)
        self._worker = CommandWorker(args, binary_override=self._custom_forgejo_path)
        self._worker.output_line.connect(self._console_write)
        self._worker.finished.connect(self._on_command_finished)
        self._worker.start()

    def _on_command_finished(self, code: int):
        self._set_buttons_enabled(True)
        if code == 0:
            self._console_write(f"\n✔ Done (exit 0)", color=GREEN)
        else:
            self._console_write(f"\n✘ Failed (exit {code})", color=RED)
        self._refresh_status()

    # ── Status refresh ────────────────────────────────────────────────

    def _refresh_status(self):
        binary = find_binary(self._custom_forgejo_path)
        if not binary:
            self._set_status_unknown()
            return

        try:
            result = subprocess.run(
                [binary, "status", "--port", str(self.inp_port.value())],
                capture_output=True, text=True, timeout=5,
            )
            output = result.stdout + result.stderr
            self.info_text.setText(output.strip() or "No output.")

            if "running" in output.lower():
                self._set_status_running()
            elif "stopped" in output.lower() or result.returncode != 0:
                self._set_status_stopped()
            else:
                self._set_status_unknown()
        except Exception:
            self._set_status_unknown()

    def _set_status_running(self):
        self.status_label.setText("● Running")
        self.status_label.setStyleSheet(
            f"color: {GREEN}; background: {BG_SURFACE}; font-weight: bold; "
            f"padding: 3px 8px; border-radius: 4px;"
        )

    def _set_status_stopped(self):
        self.status_label.setText("● Stopped")
        self.status_label.setStyleSheet(
            f"color: {RED}; background: {BG_SURFACE}; font-weight: bold; "
            f"padding: 3px 8px; border-radius: 4px;"
        )

    def _set_status_unknown(self):
        self.status_label.setText("● Unknown")
        self.status_label.setStyleSheet(
            f"color: {FG_SUBTLE}; background: {BG_SURFACE}; "
            f"padding: 3px 8px; border-radius: 4px;"
        )

    # ── Console helpers ───────────────────────────────────────────────

    def _console_write(self, line: str, color: str = FG_TEXT):
        self.console.setTextColor(QColor(color))
        self.console.append(line)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def _flush_log_buffer(self):
        if not self._log_buffer:
            return

        lines, self._log_buffer[:] = self._log_buffer[:], []

        MAX_LINES = 2000
        doc  = self.log_view.document()
        cur  = self.log_view.textCursor()

        self.log_view.setUpdatesEnabled(False)

        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText("\n".join(lines) + "\n")

        while doc.blockCount() > MAX_LINES + 1:
            trim = QTextCursor(doc.begin())
            trim.select(QTextCursor.SelectionType.BlockUnderCursor)
            trim.removeSelectedText()
            trim.deleteChar()

        self.log_view.setUpdatesEnabled(True)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _on_log_finished(self, _code: int):
        self._log_timer.stop()
        self._flush_log_buffer()
        self.btn_logs.setText("📄  Show Logs")

    def _append_log(self, widget: QTextEdit, line: str):
        widget.setTextColor(QColor(FG_TEXT))
        widget.append(line)
        widget.moveCursor(QTextCursor.MoveOperation.End)

    def _set_buttons_enabled(self, enabled: bool):
        for name in ("btn_setup", "btn_start", "btn_stop", "btn_restart",
                     "btn_uninstall", "btn_email_apply",
                     "btn_bin_install", "btn_bin_update"):
            if hasattr(self, name):
                getattr(self, name).setEnabled(enabled)

    # ── Cleanup ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._log_timer.stop()
        if self._log_worker and self._log_worker.isRunning():
            self._log_worker.stop()
            self._log_worker.wait(2000)
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
        if self._bin_check_worker and self._bin_check_worker.isRunning():
            self._bin_check_worker.wait(2000)
        event.accept()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    win = ForgejoForgeGUI(app)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
