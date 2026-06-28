# gui/tabs/binary.py
"""Binary tab — detect installed forgejo/gitea binary, path override, install/update."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from forge.constants import FG_SUBTLE, FG_TEXT, GREEN, PEACH, RED, YELLOW
from forge.utils.binary import find_installer_binary


class BinaryTab(QWidget):
    """🔧 Binary tab widget.

    Owns the detected-binary info labels, path override field, and
    install/update/check buttons.  MainWindow drives the BinaryCheckWorker
    and calls the ``update_*`` methods with results.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── public interface ──────────────────────────────────────────────

    def get_path_override(self) -> str:
        return self.inp_bin_path.text().strip()

    def set_path_field(self, path: str):
        if not self.inp_bin_path.text():
            self.inp_bin_path.setText(path)

    def clear_path_field(self):
        self.inp_bin_path.clear()

    def set_detecting(self):
        self.lbl_bin_name.setText("⏳ detecting…")
        self.lbl_bin_latest.setText("⏳ fetching…")
        self.btn_bin_detect.setEnabled(False)
        self.btn_bin_check.setEnabled(False)

    def set_detect_done(self):
        self.btn_bin_detect.setEnabled(True)
        self.btn_bin_check.setEnabled(True)

    def update_from_result(self, data: dict):
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

        self.set_path_field(data["path"])

    def show_detect_error(self):
        self.lbl_bin_name.setText("not found")
        self.lbl_bin_name.setStyleSheet(f"color: {RED}; font-weight: bold;")
        for lbl in (self.lbl_bin_path, self.lbl_bin_installed, self.lbl_bin_latest):
            lbl.setText("—")

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        lay   = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        lay.addWidget(self._make_info_group())
        lay.addWidget(self._make_path_group())
        lay.addWidget(self._make_actions_group())
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        outer.addWidget(scroll)

    def _make_info_group(self) -> QGroupBox:
        grp = QGroupBox("Detected binary")
        lay = QVBoxLayout(grp)
        lay.setSpacing(8)

        def _row(label_text: str) -> QLabel:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(110)
            lbl.setStyleSheet(f"color: {FG_SUBTLE};")
            val = QLabel("—")
            val.setStyleSheet(f"color: {FG_TEXT}; font-weight: bold;")
            val.setWordWrap(True)
            row.addWidget(lbl)
            row.addWidget(val, stretch=1)
            lay.addLayout(row)
            return val

        self.lbl_bin_name      = _row("Binary")
        self.lbl_bin_path      = _row("Path")
        self.lbl_bin_installed = _row("Installed")
        self.lbl_bin_latest    = _row("Latest")

        detect_row = QHBoxLayout()
        self.btn_bin_detect = QPushButton("⟳  Auto Detect")
        self.btn_bin_detect.setFixedHeight(44)
        detect_row.addStretch()
        detect_row.addWidget(self.btn_bin_detect)
        lay.addLayout(detect_row)

        return grp

    def _make_path_group(self) -> QGroupBox:
        grp = QGroupBox("Path override")
        lay = QVBoxLayout(grp)

        path_row = QHBoxLayout()
        self.inp_bin_path = QLineEdit()
        self.inp_bin_path.setPlaceholderText("/usr/local/bin/forgejo  (leave empty for auto)")
        path_row.addWidget(self.inp_bin_path, stretch=1)

        self.btn_bin_auto = QPushButton("Auto")
        self.btn_bin_auto.setFixedWidth(80)
        self.btn_bin_auto.setFixedHeight(44)
        path_row.addWidget(self.btn_bin_auto)

        self.btn_bin_set_path = QPushButton("Set Path")
        self.btn_bin_set_path.setFixedHeight(44)
        path_row.addWidget(self.btn_bin_set_path)

        lay.addLayout(path_row)

        note = QLabel(
            "💡 'Auto' scans PATH + /usr/local/bin + ~/.local/bin\n"
            "   'Set Path' uses whatever you type above for this session"
        )
        note.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        lay.addWidget(note)

        installer_path = find_installer_binary() or "not found"
        inst_note = QLabel(f"Installer (forgejo-main): {installer_path}")
        inst_note.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        lay.addWidget(inst_note)

        return grp

    def _make_actions_group(self) -> QGroupBox:
        grp = QGroupBox("Actions")
        lay = QHBoxLayout(grp)
        lay.setSpacing(10)

        self.btn_bin_install = QPushButton("⬇  Install")
        self.btn_bin_install.setObjectName("btn_bin_install")
        self.btn_bin_install.setFixedHeight(52)

        self.btn_bin_update = QPushButton("⬆  Update")
        self.btn_bin_update.setObjectName("btn_bin_update")
        self.btn_bin_update.setFixedHeight(52)

        self.btn_bin_check = QPushButton("⟳  Version Check")
        self.btn_bin_check.setObjectName("btn_bin_check")
        self.btn_bin_check.setFixedHeight(52)

        lay.addWidget(self.btn_bin_install)
        lay.addWidget(self.btn_bin_update)
        lay.addStretch()
        lay.addWidget(self.btn_bin_check)

        return grp
