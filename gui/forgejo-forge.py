#!/usr/bin/env python3
"""
forgejo-forge GUI
PyQt6 frontend for the forgejo-forge CLI binary.
"""

import os
import sys
import shutil
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QSpinBox,
    QTabWidget, QFrame, QSizePolicy, QMessageBox, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QProcess
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor

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

    def __init__(self, args: list[str], parent=None):
        super().__init__(parent)
        self.args = args

    def run(self):
        binary = find_binary()
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


class LogFollowWorker(QThread):
    """Follows gitea logs (blocking tail -f or journalctl -f)."""
    output_line = pyqtSignal(str)
    finished    = pyqtSignal(int)

    def __init__(self, args: list[str], parent=None):
        super().__init__(parent)
        self.args = args
        self._proc = None

    def run(self):
        binary = find_binary()
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_binary() -> str | None:
    """Locate forgejo-forge binary.

    Search order:
    1. PATH  (works after 'make install')
    2. Same directory as this executable  (frozen PyInstaller build:
       both forgejo-forge and forgejo-forge-gui live in bin/)
    3. ./bin/ relative to CWD  (running from source: python3 gui/forgejo-forge.py)
    4. ../bin/ relative to script location
    """
    # 1. PATH
    if path := shutil.which(BINARY_NAME):
        return path

    # 2. Same dir as the running executable (frozen or not)
    #    sys.executable points to the PyInstaller bundle when frozen,
    #    or to the python interpreter otherwise.
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
        tabs.addTab(self._make_logs_tab(),    "📄  Logs")
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

        binary = find_binary() or "not found"
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
        if not find_binary():
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
        # Pass 'y' to stdin confirmation prompt
        binary = find_binary()
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
            self._log_worker.stop()
            self._log_worker.wait()
            self._log_worker = None
            self.btn_logs.setText("📄  Show Logs")
            return

        args = ["logs", f"-n{self.inp_lines.value()}"]
        if self.chk_follow.isChecked():
            args.append("-f")

        self.log_view.clear()
        self._log_worker = LogFollowWorker(args)
        self._log_worker.output_line.connect(
            lambda line: self._append_log(self.log_view, line)
        )
        self._log_worker.finished.connect(lambda _: self.btn_logs.setText("📄  Show Logs"))
        self._log_worker.start()
        self.btn_logs.setText("⏹  Stop Logs")

    # ── Generic command runner ────────────────────────────────────────

    def _run_command(self, args: list[str]):
        if self._worker and self._worker.isRunning():
            self._console_write("⚠ Another command is still running.", color=YELLOW)
            return

        self._set_buttons_enabled(False)
        self._worker = CommandWorker(args)
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
        binary = find_binary()
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

    def _append_log(self, widget: QTextEdit, line: str):
        widget.setTextColor(QColor(FG_TEXT))
        widget.append(line)
        widget.moveCursor(QTextCursor.MoveOperation.End)

    def _set_buttons_enabled(self, enabled: bool):
        for name in ("btn_setup", "btn_start", "btn_stop", "btn_restart", "btn_uninstall"):
            if hasattr(self, name):
                getattr(self, name).setEnabled(enabled)

    # ── Cleanup ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self._log_worker and self._log_worker.isRunning():
            self._log_worker.stop()
            self._log_worker.wait()
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        event.accept()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # HiDPI
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    win = ForgejoForgeGUI(app)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
