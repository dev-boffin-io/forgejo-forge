# gui/workers/base.py
"""Background QThread workers for running CLI subcommands."""

import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

from forge.utils.ansi import strip_ansi
from forge.utils.binary import find_binary, find_installer_binary


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
