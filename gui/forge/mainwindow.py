# gui/mainwindow.py
"""Main application window — wires tabs, workers, and timers together."""

import os
import subprocess

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QDialog, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from forge.constants import (
    ACCENT, APP_NAME, APP_VERSION, BINARY_NAME,
    BG_SURFACE, FG_SUBTLE, FG_TEXT, GREEN, RED, STYLE, YELLOW,
)
from forge.dialogs.ini_editor import IniEditorDialog
from forge.tabs.binary import BinaryTab
from forge.tabs.control import ControlTab
from forge.tabs.email import EmailTab
from forge.tabs.git_manager import GitManagerTab
from forge.tabs.logs import LogsTab
from forge.tabs.runner import RunnerTab
from forge.tabs.setup import SetupTab
from forge.utils.binary import find_binary, find_installer_binary, screen_aware_size
from forge.workers.base import CommandWorker, InstallerWorker, LogFollowWorker
from forge.workers.binary_check import BinaryCheckWorker


class ForgejoForgeGUI(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        w, h = screen_aware_size(app)
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(w, h)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(STYLE)

        self._worker: CommandWorker | None = None
        self._log_worker: LogFollowWorker | None = None
        self._bin_check_worker: BinaryCheckWorker | None = None
        self._log_buffer: list[str] = []
        self._custom_forgejo_path: str = ""
        self._custom_runner_path: str = ""

        # Drains _log_buffer → log_view every 100 ms
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(100)
        self._log_timer.timeout.connect(self._flush_log_buffer)

        self._build_ui()
        self._connect_signals()
        self._check_binary()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        root.addWidget(self._make_header())

        self.status_label = QLabel("● Unknown")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self.status_label)

        # Tabs
        self.tab_setup    = SetupTab()
        self.tab_control  = ControlTab()
        self.tab_email    = EmailTab()
        self.tab_runner   = RunnerTab()
        self.tab_logs     = LogsTab()
        self.tab_binary   = BinaryTab()
        self.tab_git      = GitManagerTab()

        tabs = QTabWidget()
        tabs.addTab(self.tab_setup,   "⚙  Setup")
        tabs.addTab(self.tab_control, "▶  Control")
        tabs.addTab(self.tab_email,   "📧  Email")
        tabs.addTab(self.tab_runner,  "🏃  Runner")
        tabs.addTab(self.tab_logs,    "📄  Logs")
        tabs.addTab(self.tab_binary,  "🔧  Binary")
        tabs.addTab(self.tab_git,     "⬡  Git")
        root.addWidget(tabs, stretch=1)

        root.addWidget(self._make_console())

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(5000)
        self._refresh_status()

    def _make_header(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        title = QLabel(f"🦊  {APP_NAME}")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {ACCENT};")

        binary = find_binary(self._custom_forgejo_path) or "not found"
        sub    = QLabel(f"binary: {binary}")
        sub.setStyleSheet(f"font-size: 22px; color: {FG_SUBTLE};")

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(sub)
        return w

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

    # ── Signal wiring ─────────────────────────────────────────────────

    def _connect_signals(self):
        # Setup tab
        self.tab_setup.btn_setup.clicked.connect(self._run_setup)
        self.tab_setup.btn_actions_apply.clicked.connect(
            lambda: self._run_command(["config", "enable-actions"])
        )
        self.tab_setup.btn_cfg_edit.clicked.connect(self._open_ini_editor)

        # Control tab
        self.tab_control.btn_start.clicked.connect(self._run_start)
        self.tab_control.btn_stop.clicked.connect(self._run_stop)
        self.tab_control.btn_restart.clicked.connect(self._run_restart)
        self.tab_control.btn_refresh.clicked.connect(self._refresh_status)
        self.tab_control.btn_uninstall.clicked.connect(self._run_uninstall)

        # Email tab
        self.tab_email.btn_email_apply.clicked.connect(self._run_email_setup)
        self.tab_email.btn_restart.clicked.connect(self._run_restart)

        # Logs tab
        self.tab_logs.btn_logs.clicked.connect(self._toggle_logs)

        # Runner tab
        self.tab_runner.btn_runner_refresh.clicked.connect(self._runner_refresh_status)
        self.tab_runner.btn_runner_bin_auto.clicked.connect(self._runner_bin_path_auto)
        self.tab_runner.btn_runner_bin_set.clicked.connect(self._runner_bin_path_set)
        self.tab_runner.btn_runner_install.clicked.connect(
            lambda: self._runner_run(["install"])
        )
        self.tab_runner.btn_runner_uninstall.clicked.connect(self._runner_uninstall)
        self.tab_runner.btn_runner_register.clicked.connect(self._runner_register)
        self.tab_runner.btn_runner_start.clicked.connect(
            lambda: self._runner_run(["start"])
        )
        self.tab_runner.btn_runner_stop.clicked.connect(
            lambda: self._runner_run(["stop"])
        )
        self.tab_runner.btn_runner_status_btn.clicked.connect(
            lambda: self._runner_run(["status"])
        )

        # Binary tab
        self.tab_binary.btn_bin_detect.clicked.connect(self._run_detect_binary)
        self.tab_binary.btn_bin_check.clicked.connect(self._run_detect_binary)
        self.tab_binary.btn_bin_auto.clicked.connect(self._bin_path_auto)
        self.tab_binary.btn_bin_set_path.clicked.connect(self._bin_path_set)
        self.tab_binary.btn_bin_install.clicked.connect(self._run_binary_install)
        self.tab_binary.btn_bin_update.clicked.connect(self._run_binary_update)

        # Deferred startup checks
        QTimer.singleShot(500, self._run_detect_binary)
        QTimer.singleShot(600, self._runner_refresh_status)

    # ── Setup slots ───────────────────────────────────────────────────

    def _run_setup(self):
        if args := self.tab_setup.get_setup_args():
            self._run_command(args)

    # ── Control slots ─────────────────────────────────────────────────

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

    # ── Email slots ───────────────────────────────────────────────────

    def _run_email_setup(self):
        if args := self.tab_email.get_email_args():
            self._run_command(args)

    # ── app.ini editor ────────────────────────────────────────────────

    def _open_ini_editor(self):
        binary = find_binary(self._custom_forgejo_path)
        if not binary:
            QMessageBox.warning(self, "Binary not found",
                                "Could not locate the forgejo-forge binary.")
            return

        try:
            result = subprocess.run(
                [binary, "config", "raw-get"],
                capture_output=True, text=True, timeout=10,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read app.ini:\n{e}")
            return

        if result.returncode != 0:
            QMessageBox.critical(
                self, "Error",
                f"Failed to read app.ini:\n{(result.stderr or result.stdout).strip()}",
            )
            return

        dialog = IniEditorDialog(result.stdout, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_content = dialog.text_edit.toPlainText()
        if not new_content.endswith("\n"):
            new_content += "\n"

        try:
            result = subprocess.run(
                [binary, "config", "raw-set"],
                input=new_content, capture_output=True, text=True, timeout=10,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to write app.ini:\n{e}")
            return

        if result.returncode != 0:
            QMessageBox.critical(
                self, "Error",
                f"Failed to write app.ini:\n{(result.stderr or result.stdout).strip()}",
            )
            return

        self._console_write(result.stdout.strip(), color=GREEN)
        self._console_write(
            "⚠ Restart Forgejo for changes to take effect (Control tab).",
            color=YELLOW,
        )

    # ── Logs slots ────────────────────────────────────────────────────

    def _toggle_logs(self):
        if self._log_worker and self._log_worker.isRunning():
            self._log_timer.stop()
            self._log_worker.stop()
            self._log_worker = None
            self.tab_logs.btn_logs.setText("📄  Show Logs")
            return

        args = ["logs", f"-n{self.tab_logs.n_lines()}"]
        if self.tab_logs.follow_checked():
            args.append("-f")

        self.tab_logs.clear_log()
        self._log_buffer.clear()

        self._log_worker = LogFollowWorker(args, binary_override=self._custom_forgejo_path)
        self._log_worker.output_line.connect(self._log_buffer.append)
        self._log_worker.finished.connect(self._on_log_finished)
        self._log_worker.start()
        self._log_timer.start()
        self.tab_logs.btn_logs.setText("⏹  Stop Logs")

    # ── Runner slots ──────────────────────────────────────────────────

    def _runner_bin_path_auto(self):
        self._custom_runner_path = ""
        self.tab_runner.inp_runner_bin_path.clear()
        self._runner_refresh_status()

    def _runner_bin_path_set(self):
        path = self.tab_runner.get_runner_path_override()
        if path and not (os.path.isfile(path) and os.access(path, os.X_OK)):
            QMessageBox.warning(
                self, "Invalid path",
                f"'{path}' is not an executable file.\nCheck the path and try again.",
            )
            return
        self._custom_runner_path = path
        self._runner_refresh_status()

    def _runner_run(self, args: list):
        if self._worker and self._worker.isRunning():
            self._console_write("⚠ Another command is still running.", color=YELLOW)
            return
        self.tab_runner.set_buttons_enabled(False)
        full_args = ["runner"] + args
        if self._custom_runner_path:
            full_args = ["runner", "--runner-bin", self._custom_runner_path] + args
        self._worker = CommandWorker(full_args, binary_override=self._custom_forgejo_path)
        self._worker.output_line.connect(self._console_write)
        self._worker.finished.connect(self._on_runner_finished)
        self._worker.start()

    def _on_runner_finished(self, code: int):
        self.tab_runner.set_buttons_enabled(True)
        if code == 0:
            self._console_write("\n✔ Done (exit 0)", color=GREEN)
        else:
            self._console_write(f"\n✘ Failed (exit {code})", color=RED)
        QTimer.singleShot(300, self._runner_refresh_status)

    def _runner_uninstall(self):
        reply = QMessageBox.question(
            self, "Confirm runner uninstall",
            "Remove the runner binary, config, and PID file?\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._runner_run(["uninstall"])

    def _runner_register(self):
        if args := self.tab_runner.get_register_args():
            self._runner_run(args)

    def _runner_refresh_status(self):
        try:
            binary = find_binary(self._custom_forgejo_path)
            if not binary:
                self.tab_runner.set_status_label("● Binary missing", RED)
                return
            args = [binary, "runner", "status"]
            if self._custom_runner_path:
                args = [binary, "runner", "--runner-bin", self._custom_runner_path, "status"]
            result = subprocess.run(args, capture_output=True, text=True, timeout=5)
            out = (result.stdout + result.stderr).lower()

            # Auto-fill runner binary path if we get one from output
            for line in (result.stdout + result.stderr).splitlines():
                if "runner binary" in line.lower() and ":" in line:
                    detected = line.split(":", 1)[1].strip()
                    if detected and detected != "not installed":
                        self.tab_runner.set_runner_path_field(detected)
                    break

            if "running" in out:
                self.tab_runner.set_status_label("● Running", GREEN)
            elif "not installed" in out or "binary not found" in out:
                self.tab_runner.set_status_label("● Not installed", RED)
            elif "stopped" in out:
                self.tab_runner.set_status_label("● Stopped", RED)
                if "log lines" in out:
                    self._console_write(
                        "\n" + (result.stdout + result.stderr).strip(), color=YELLOW
                    )
            else:
                self.tab_runner.set_status_label("● Unknown", FG_SUBTLE)
        except Exception:
            self.tab_runner.set_status_label("● Unknown", FG_SUBTLE)

    # ── Binary tab slots ──────────────────────────────────────────────

    def _run_detect_binary(self):
        if self._bin_check_worker and self._bin_check_worker.isRunning():
            return
        self.tab_binary.set_detecting()
        self._bin_check_worker = BinaryCheckWorker(self._custom_forgejo_path)
        self._bin_check_worker.result.connect(self._on_detect_result)
        self._bin_check_worker.error.connect(self._on_detect_error)
        self._bin_check_worker.finished.connect(self.tab_binary.set_detect_done)
        self._bin_check_worker.start()

    def _on_detect_result(self, data: dict):
        self.tab_binary.update_from_result(data)
        self._console_write(
            f"✔ Detected: {data['binary']} {data['installed']}  (latest: {data['latest']})",
            color=GREEN,
        )

    def _on_detect_error(self, msg: str):
        self.tab_binary.show_detect_error()
        self._console_write(f"⚠ {msg}", color=YELLOW)

    def _bin_path_auto(self):
        self._custom_forgejo_path = ""
        self.tab_binary.clear_path_field()
        self._run_detect_binary()

    def _bin_path_set(self):
        path = self.tab_binary.get_path_override()
        if path and not (os.path.isfile(path) and os.access(path, os.X_OK)):
            QMessageBox.warning(
                self, "Invalid path",
                f"'{path}' is not an executable file.\nCheck the path and try again.",
            )
            return
        self._custom_forgejo_path = path
        self._run_detect_binary()

    def _run_binary_install(self):
        if not find_installer_binary():
            QMessageBox.critical(
                self, "Installer not found",
                "forgejo-main binary not found.\n\nRun 'make installer' to build it first.",
            )
            return
        self._run_installer_command(["install"])

    def _run_binary_update(self):
        if not find_installer_binary():
            QMessageBox.critical(
                self, "Installer not found",
                "forgejo-main binary not found.\n\nRun 'make installer' to build it first.",
            )
            return
        self._run_installer_command(["update"])

    def _run_installer_command(self, args: list[str]):
        if self._worker and self._worker.isRunning():
            self._console_write("⚠ Another command is still running.", color=YELLOW)
            return
        self._set_buttons_enabled(False)
        worker = InstallerWorker(args)
        worker.output_line.connect(self._console_write)
        worker.finished.connect(self._on_installer_finished)
        self._worker = worker  # type: ignore[assignment]
        self._worker.start()

    def _on_installer_finished(self, code: int):
        self._set_buttons_enabled(True)
        if code == 0:
            self._console_write("\n✔ Done (exit 0)", color=GREEN)
            QTimer.singleShot(800, self._run_detect_binary)
        else:
            self._console_write(f"\n✘ Failed (exit {code})", color=RED)

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
            self._console_write("\n✔ Done (exit 0)", color=GREEN)
        else:
            self._console_write(f"\n✘ Failed (exit {code})", color=RED)
        self._refresh_status()

    # ── Status refresh ────────────────────────────────────────────────

    def _check_binary(self):
        if not find_binary(self._custom_forgejo_path):
            self._console_write(
                f"⚠  '{BINARY_NAME}' binary not found.\n"
                f"   Run 'make build' first, or add bin/ to PATH.\n",
                color=YELLOW,
            )

    def _refresh_status(self):
        binary = find_binary(self._custom_forgejo_path)
        if not binary:
            self._set_status_unknown()
            return
        try:
            result = subprocess.run(
                [binary, "status", "--port", str(self.tab_setup.current_port())],
                capture_output=True, text=True, timeout=5,
            )
            output = result.stdout + result.stderr
            self.tab_control.set_info_text(output)

            lower = output.lower()
            if "running" in lower:
                self._set_status_running()
            elif "stopped" in lower or result.returncode != 0:
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
        doc = self.tab_logs.log_view.document()
        cur = self.tab_logs.log_view.textCursor()

        self.tab_logs.log_view.setUpdatesEnabled(False)
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText("\n".join(lines) + "\n")

        while doc.blockCount() > MAX_LINES + 1:
            trim = QTextCursor(doc.begin())
            trim.select(QTextCursor.SelectionType.BlockUnderCursor)
            trim.removeSelectedText()
            trim.deleteChar()

        self.tab_logs.log_view.setUpdatesEnabled(True)
        self.tab_logs.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _on_log_finished(self, _code: int):
        self._log_timer.stop()
        self._flush_log_buffer()
        self.tab_logs.btn_logs.setText("📄  Show Logs")

    def _set_buttons_enabled(self, enabled: bool):
        for name in (
            "btn_setup", "btn_start", "btn_stop", "btn_restart",
            "btn_uninstall", "btn_email_apply",
            "btn_bin_install", "btn_bin_update",
            "btn_runner_install", "btn_runner_uninstall",
            "btn_runner_register", "btn_runner_start",
            "btn_runner_stop", "btn_runner_status_btn",
        ):
            # Buttons live on various tab widgets now
            for tab in (
                self.tab_setup, self.tab_control, self.tab_email,
                self.tab_runner, self.tab_binary,
            ):
                if widget := getattr(tab, name, None):
                    widget.setEnabled(enabled)

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
