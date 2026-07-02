"""
Forge Git Manager — tabbed PyQt6 GUI
Tabs: Git Binary · Extractor · Git Init · Git Remote · Git Push · Source Clone
Cross-platform: Windows, macOS, Linux, Termux, proot-distro.
Python 3.9+ compatible.
"""
from __future__ import annotations

import sys
import os
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QListWidget, QAbstractItemView, QTextEdit, QMessageBox,
    QFrame, QSizePolicy, QProgressBar, QTabWidget, QCheckBox,
    QScrollArea, QDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase

from forge_git_manager.theme import apply_theme, STYLESHEET
from forge_git_manager.git_config import (
    auto_detect_git, get_git_version, get_install_commands,
    set_git_path, get_git_path, _is_termux, _is_root,
)
from forge_git_manager.workers import (
    ExtractorWorker,
    GitInitWorker,
    GitRemoteWorker,
    GitPushWorker,
    CloneWorker,
    DeleteCloneWorker,
    GitBinaryWorker,
)

# ── Cross-platform default paths ──────────────────────────────────────────────
def _default_desktop() -> str:
    return str(Path.home() / "Desktop")

def _default_projects() -> str:
    return str(Path.home() / "Desktop" / "my_projects")

def _default_bare_repo() -> str:
    # Sensible per-OS default; user should browse to their actual path
    if platform.system() == "Windows":
        return str(Path.home() / "forgejo" / "repositories")
    return str(Path.home() / "forge-storage" / "forgejo" / "repositories")

DEFAULT_BARE_REPO_DIR = _default_bare_repo()
DEFAULT_PROJECTS_DIR  = _default_projects()
DEFAULT_DESKTOP_DIR   = _default_desktop()
DEFAULT_USERNAME      = ""
DEFAULT_TOKEN         = ""
DEFAULT_HOST          = "localhost:3000"
DEFAULT_REMOTE_NAME   = "local"
DEFAULT_BRANCH        = "main"


# ── Shared UI helpers ─────────────────────────────────────────────────────────

class SectionLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text.upper())
        self.setObjectName("sectionLabel")


class FolderInputRow(QFrame):
    def __init__(self, label_text: str, placeholder: str, default_text: str = "",
                 show_cwd_btn: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("folderInputRow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(SectionLabel(label_text))

        row = QHBoxLayout()
        row.setSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setText(default_text)
        self.input.setObjectName("pathInput")

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        row.addWidget(self.input)
        row.addWidget(self.browse_btn)

        if show_cwd_btn:
            self.cwd_btn = QPushButton("📂 Use Current Dir")
            self.cwd_btn.setObjectName("cwdBtn")
            self.cwd_btn.setFixedWidth(140)
            self.cwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cwd_btn.setToolTip("Set to the current working directory")
            self.cwd_btn.clicked.connect(self._use_cwd)
            row.addWidget(self.cwd_btn)

        layout.addLayout(row)

    def _use_cwd(self):
        self.input.setText(os.getcwd())


class FieldInputRow(QFrame):
    """Single-line text input without a browse button."""
    def __init__(self, label_text: str, placeholder: str, default_text: str = "",
                 echo_mode=QLineEdit.EchoMode.Normal, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(SectionLabel(label_text))
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setText(default_text)
        self.input.setObjectName("pathInput")
        self.input.setEchoMode(echo_mode)
        layout.addWidget(self.input)


def make_log_area() -> QTextEdit:
    log = QTextEdit()
    log.setObjectName("logArea")
    log.setReadOnly(True)
    log.setMinimumHeight(100)
    log.setPlaceholderText("Output will appear here...")
    return log


def make_progress_bar() -> QProgressBar:
    pb = QProgressBar()
    pb.setObjectName("progressBar")
    pb.setRange(0, 0)
    pb.setVisible(False)
    pb.setFixedHeight(6)
    pb.setTextVisible(False)
    return pb


def make_scrollable(widget_builder):
    """Wrap a widget-building function in a QScrollArea."""
    outer = QWidget()
    outer.setObjectName("tabPage")
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    outer_layout.addWidget(scroll)

    inner = QWidget()
    inner.setObjectName("tabPage")
    scroll.setWidget(inner)
    return outer, inner


# ── Tab 1 — Extractor ─────────────────────────────────────────────────────────

class ExtractorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Info
        info = QFrame()
        info.setObjectName("infoBox")
        info_lbl = QLabel(
            "📋  Equivalent to git_init.sh\n"
            "Scans a folder of bare .git repos and archives each one as a .zip file."
        )
        info_lbl.setObjectName("infoText")
        info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(info_lbl)
        layout.addWidget(info)

        # Source bare repo dir
        self.src_row = FolderInputRow(
            "Source Folder (bare .git repos)",
            "Path to Forgejo bare repos...",
            default_text=DEFAULT_BARE_REPO_DIR,
        )
        self.src_row.browse_btn.clicked.connect(self._browse_source)
        layout.addWidget(self.src_row)

        # Scan
        scan_btn = QPushButton("🔍  Scan for Repositories")
        scan_btn.setObjectName("scanBtn")
        scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_btn.clicked.connect(self._scan)
        layout.addWidget(scan_btn)

        # Repo list
        layout.addWidget(SectionLabel("Select Repositories  ·  Ctrl+Click for multi-select"))
        self.repo_list = QListWidget()
        self.repo_list.setObjectName("repoList")
        self.repo_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.repo_list.setMinimumHeight(100)
        layout.addWidget(self.repo_list)

        # Output dir
        self.out_row = FolderInputRow("Output Folder", "Where to save .zip files...")
        self.out_row.browse_btn.clicked.connect(self._browse_output)
        layout.addWidget(self.out_row)

        # Extract button
        self.extract_btn = QPushButton("🚀  Extract & Zip Selected Projects")
        self.extract_btn.setObjectName("extractBtn")
        self.extract_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.extract_btn.clicked.connect(self._start_extraction)
        layout.addWidget(self.extract_btn)

        self.progress_bar = make_progress_bar()
        layout.addWidget(self.progress_bar)

        layout.addWidget(SectionLabel("Progress Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)

    def _browse_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if folder:
            self.src_row.input.setText(folder)
            self._scan()

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.out_row.input.setText(folder)

    def _scan(self):
        self.repo_list.clear()
        src = self.src_row.input.text().strip()
        if not os.path.exists(src):
            QMessageBox.warning(self, "Warning", "Source folder not found!")
            return
        repos = sorted(
            d for d in os.listdir(src)
            if os.path.isdir(os.path.join(src, d)) and d.endswith(".git")
        )
        if repos:
            self.repo_list.addItems(repos)
            self.log.append(f"✅  Found {len(repos)} repositor{'y' if len(repos)==1 else 'ies'}.")
        else:
            self.log.append("⚠️  No bare '.git' repositories found.")

    def _start_extraction(self):
        src = self.src_row.input.text().strip()
        out = self.out_row.input.text().strip()
        selected = self.repo_list.selectedItems()

        if not selected:
            QMessageBox.warning(self, "Warning", "Please select at least one repository.")
            return
        if not out:
            QMessageBox.warning(self, "Warning", "Please choose an output folder.")
            return

        os.makedirs(out, exist_ok=True)
        repos = [i.text() for i in selected]

        self.extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log.clear()
        self.log.append(f"Starting extraction of {len(repos)} project(s)...\n")

        self.worker = ExtractorWorker(repos, src, out)
        self.worker.progress_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._done)
        self.worker.start()

    def _done(self):
        self.extract_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Complete", "All selected projects zipped successfully!")


def _smart_merge(existing: str, new_content: str) -> str:
    """
    Merge new_content into existing .gitignore without duplicating lines.
    - Comments and blank lines from new_content are added only if the
      section header isn't already present.
    - Pattern lines are added only if not already in existing (case-insensitive).
    """
    existing_lines = set(
        line.strip().lower()
        for line in existing.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    existing_headers = set(
        line.strip().lower()
        for line in existing.splitlines()
        if line.strip().startswith("#")
    )

    to_add: list[str] = []
    for line in new_content.splitlines():
        stripped = line.strip()
        if not stripped:
            to_add.append(line)
        elif stripped.startswith("#"):
            if stripped.lower() not in existing_headers:
                to_add.append(line)
        else:
            if stripped.lower() not in existing_lines:
                to_add.append(line)

    # Remove leading/trailing blank lines from to_add
    while to_add and not to_add[0].strip():
        to_add.pop(0)
    while to_add and not to_add[-1].strip():
        to_add.pop()

    if not to_add:
        return existing  # nothing new to add

    return existing.rstrip() + "\n\n# === Merged by Forge Git Manager ===\n" + "\n".join(to_add) + "\n"


class _ConflictDialog(QDialog):
    """Single-file conflict dialog: Overwrite / Merge / Skip."""
    chosen: str = "skip"

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Already Exists")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        msg = QLabel(
            f"<b>.gitignore already exists:</b><br>"
            f"<code>{path}</code><br><br>"
            "What would you like to do?"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        ow = QPushButton("🔄  Overwrite")
        ow.setObjectName("dangerBtn")
        ow.setCursor(Qt.CursorShape.PointingHandCursor)
        ow.clicked.connect(lambda: self._pick("overwrite"))

        mg = QPushButton("🔀  Merge")
        mg.setObjectName("extractBtn")
        mg.setCursor(Qt.CursorShape.PointingHandCursor)
        mg.clicked.connect(lambda: self._pick("merge"))

        sk = QPushButton("⏭️  Skip")
        sk.setObjectName("browseBtn")
        sk.setCursor(Qt.CursorShape.PointingHandCursor)
        sk.clicked.connect(lambda: self._pick("skip"))

        btn_row.addWidget(ow)
        btn_row.addWidget(mg)
        btn_row.addWidget(sk)
        layout.addLayout(btn_row)

        note = QLabel(
            "<small>"
            "<b>Overwrite</b> — replace existing file completely.<br>"
            "<b>Merge</b> — keep existing lines, add only new patterns (no duplicates).<br>"
            "<b>Skip</b> — leave the existing file untouched."
            "</small>"
        )
        note.setWordWrap(True)
        note.setObjectName("sectionLabel")
        layout.addWidget(note)

    def _pick(self, choice: str):
        self.chosen = choice
        self.accept()


class _BatchConflictDialog(QDialog):
    """Multi-folder conflict dialog: apply one policy to all conflicts."""
    chosen: str = "skip"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Existing .gitignore Files Detected")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        msg = QLabel(
            "Some sub-folders already contain a <b>.gitignore</b> file.<br><br>"
            "Choose how to handle <b>all</b> conflicts:"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        ow = QPushButton("🔄  Overwrite All")
        ow.setObjectName("dangerBtn")
        ow.setCursor(Qt.CursorShape.PointingHandCursor)
        ow.clicked.connect(lambda: self._pick("overwrite"))

        mg = QPushButton("🔀  Merge All")
        mg.setObjectName("extractBtn")
        mg.setCursor(Qt.CursorShape.PointingHandCursor)
        mg.clicked.connect(lambda: self._pick("merge"))

        sk = QPushButton("⏭️  Skip Existing")
        sk.setObjectName("browseBtn")
        sk.setCursor(Qt.CursorShape.PointingHandCursor)
        sk.clicked.connect(lambda: self._pick("skip"))

        btn_row.addWidget(ow)
        btn_row.addWidget(mg)
        btn_row.addWidget(sk)
        layout.addLayout(btn_row)

        note = QLabel(
            "<small>"
            "<b>Overwrite All</b> — replace every existing file.<br>"
            "<b>Merge All</b> — add only new patterns, skip duplicates.<br>"
            "<b>Skip Existing</b> — only write to folders without .gitignore."
            "</small>"
        )
        note.setWordWrap(True)
        note.setObjectName("sectionLabel")
        layout.addWidget(note)

    def _pick(self, choice: str):
        self.chosen = choice
        self.accept()


# ── Tab — .gitignore Generator ───────────────────────────────────────────────

class GitignoreTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self._selected: set[str] = set()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top: folder + mode (always visible) ──────────────────────────────
        top = QWidget()
        top.setObjectName("tabPage")
        tl = QVBoxLayout(top)
        tl.setContentsMargins(24, 16, 24, 8)
        tl.setSpacing(10)

        info = QFrame()
        info.setObjectName("infoBox")
        info_lbl = QLabel(
            "📋  Select one or more templates, add custom rules, then click Generate.\n"
            "     Works on the selected folder itself OR all its sub-folders."
        )
        info_lbl.setObjectName("infoText")
        info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(info_lbl)
        tl.addWidget(info)

        # Folder picker
        self.folder_row = FolderInputRow(
            "Target Folder",
            "Select folder to create .gitignore in…",
            show_cwd_btn=True,
        )
        self.folder_row.browse_btn.clicked.connect(self._browse)
        tl.addWidget(self.folder_row)

        # Mode
        self.single_chk = QCheckBox(
            "Apply to this folder directly  (not its sub-folders)"
        )
        self.single_chk.setObjectName("modeCheck")
        self.single_chk.setChecked(True)
        tl.addWidget(self.single_chk)

        outer.addWidget(top)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#2e3347;max-height:1px;border:none;")
        outer.addWidget(div)

        # ── Scrollable: templates + custom + preview + generate ───────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        container = QWidget()
        container.setObjectName("tabPage")
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 12, 24, 16)
        layout.setSpacing(12)

        # Template grid
        layout.addWidget(SectionLabel("Select Templates  ·  Click to toggle  ·  Multiple OK"))

        grid_widget = QWidget()
        grid_widget.setObjectName("tabPage")
        self._grid = QHBoxLayout(grid_widget)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._btn_rows: list[QHBoxLayout] = []
        self._tmpl_btns: dict[str, QPushButton] = {}

        # Build rows of 4
        from forge_git_manager.gitignore_templates import TEMPLATES
        row_layout: QHBoxLayout | None = None
        row_container_layout = QVBoxLayout()
        row_container_layout.setSpacing(6)

        for i, tmpl in enumerate(TEMPLATES):
            if i % 4 == 0:
                row_w = QWidget()
                row_w.setObjectName("tabPage")
                row_layout = QHBoxLayout(row_w)
                row_layout.setSpacing(6)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_container_layout.addWidget(row_w)

            btn = QPushButton(f"{tmpl['icon']}  {tmpl['name']}")
            btn.setObjectName("tmplBtnOff")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(140)
            btn.clicked.connect(lambda checked, n=tmpl["name"], b=btn: self._toggle(n, b))
            self._tmpl_btns[tmpl["name"]] = btn
            row_layout.addWidget(btn)  # type: ignore

        # Fill last row
        remainder = len(TEMPLATES) % 4
        if remainder:
            for _ in range(4 - remainder):
                row_layout.addStretch()  # type: ignore

        grid_frame = QFrame()
        grid_frame.setObjectName("tabPage")
        grid_frame.setLayout(row_container_layout)
        layout.addWidget(grid_frame)

        # Quick-select buttons
        qs_row = QHBoxLayout()
        qs_row.setSpacing(8)
        all_btn = QPushButton("Select All")
        all_btn.setObjectName("scanBtn")
        all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        all_btn.clicked.connect(self._select_all)
        none_btn = QPushButton("Clear All")
        none_btn.setObjectName("browseBtn")
        none_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        none_btn.clicked.connect(self._clear_all)
        qs_row.addWidget(all_btn)
        qs_row.addWidget(none_btn)
        qs_row.addStretch()
        layout.addLayout(qs_row)

        # Custom rules
        layout.addWidget(SectionLabel("Custom Rules  (appended at the end)"))
        self.custom_edit = QTextEdit()
        self.custom_edit.setObjectName("logArea")
        self.custom_edit.setPlaceholderText(
            "# Add your own patterns here, one per line\n"
            "secrets.json\n"
            "config/local.py\n"
        )
        self.custom_edit.setMinimumHeight(80)
        self.custom_edit.setMaximumHeight(140)
        layout.addWidget(self.custom_edit)

        # Preview
        layout.addWidget(SectionLabel("Preview"))
        self.preview = QTextEdit()
        self.preview.setObjectName("logArea")
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(120)
        self.preview.setPlaceholderText("Select templates above to preview…")
        layout.addWidget(self.preview)

        preview_btn = QPushButton("👁  Refresh Preview")
        preview_btn.setObjectName("scanBtn")
        preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        preview_btn.clicked.connect(self._refresh_preview)
        layout.addWidget(preview_btn)

        # Generate button
        self.gen_btn = QPushButton("✍️  Generate .gitignore")
        self.gen_btn.setObjectName("extractBtn")
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.clicked.connect(self._generate)
        layout.addWidget(self.gen_btn)

        layout.addWidget(SectionLabel("Output Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)
        layout.addStretch()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_row.input.setText(folder)

    def _toggle(self, name: str, btn: QPushButton):
        if name in self._selected:
            self._selected.discard(name)
            btn.setObjectName("tmplBtnOff")
        else:
            self._selected.add(name)
            btn.setObjectName("tmplBtnOn")
        # Force style refresh
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        self._refresh_preview()

    def _select_all(self):
        for name, btn in self._tmpl_btns.items():
            self._selected.add(name)
            btn.setObjectName("tmplBtnOn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._refresh_preview()

    def _clear_all(self):
        self._selected.clear()
        for btn in self._tmpl_btns.values():
            btn.setObjectName("tmplBtnOff")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.preview.clear()

    def _build_content(self) -> str:
        from forge_git_manager.gitignore_templates import TEMPLATES, combine_templates
        # Maintain template order
        ordered = [t["name"] for t in TEMPLATES if t["name"] in self._selected]
        content = combine_templates(ordered)
        custom = self.custom_edit.toPlainText().strip()
        if custom:
            content += f"\n\n# === Custom Rules ===\n{custom}\n"
        return content

    def _refresh_preview(self):
        content = self._build_content()
        self.preview.setPlainText(content if content.strip() else "")

    def _write_gitignore(self, folder: str, content: str,
                         conflict_policy: str = "ask") -> tuple[bool, str]:
        """
        Write .gitignore to folder.
        conflict_policy: 'ask' | 'overwrite' | 'merge' | 'skip'
        Returns (success, message).
        """
        path = os.path.join(folder, ".gitignore")
        exists = os.path.isfile(path)

        if exists:
            policy = conflict_policy
            if policy == "ask":
                dlg = _ConflictDialog(path, self)
                result = dlg.exec()
                policy = dlg.chosen  # 'overwrite' | 'merge' | 'skip'

            if policy == "skip":
                return False, f"⏭️  Skipped (already exists): {path}"

            if policy == "overwrite":
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    return True, f"✅  Overwritten: {path}"
                except Exception as e:
                    return False, f"❌  {folder}: {e}"

            if policy == "merge":
                try:
                    existing = open(path, encoding="utf-8").read()
                    merged = _smart_merge(existing, content)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(merged)
                    return True, f"🔀  Merged: {path}"
                except Exception as e:
                    return False, f"❌  {folder}: {e}"

        # File does not exist — just write
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"✅  Created: {path}"
        except Exception as e:
            return False, f"❌  {folder}: {e}"

    def _generate(self):
        folder = self.folder_row.input.text().strip()
        if not folder:
            QMessageBox.warning(self, "Warning", "Please select a target folder.")
            return
        if not self._selected:
            QMessageBox.warning(self, "Warning", "Please select at least one template.")
            return
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Warning", f"Folder not found:\n{folder}")
            return

        content = self._build_content()
        single = self.single_chk.isChecked()
        self.log.clear()

        if single:
            ok, msg = self._write_gitignore(folder, content, conflict_policy="ask")
            self.log.append(msg)
        else:
            subdirs = sorted(
                d for d in os.listdir(folder)
                if os.path.isdir(os.path.join(folder, d))
            )
            if not subdirs:
                self.log.append("⚠️  No sub-folders found.")
                return

            # For multi-folder, ask once if any conflicts exist
            has_conflict = any(
                os.path.isfile(os.path.join(folder, d, ".gitignore"))
                for d in subdirs
            )
            policy = "ask"
            if has_conflict:
                dlg = _BatchConflictDialog(self)
                dlg.exec()
                policy = dlg.chosen  # 'overwrite' | 'merge' | 'skip'

            self.log.append(f"📝  Writing .gitignore to {len(subdirs)} sub-folder(s)...\n")
            ok_count = 0
            for d in subdirs:
                ok, msg = self._write_gitignore(
                    os.path.join(folder, d), content,
                    conflict_policy=policy,
                )
                self.log.append(msg)
                if ok:
                    ok_count += 1
            self.log.append(f"\n🎉  Done! {ok_count}/{len(subdirs)} .gitignore files written.")


# ── Tab 2 — Git Init ──────────────────────────────────────────────────────────

class GitInitTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Info box
        info = QFrame()
        info.setObjectName("infoBox")
        info_lbl = QLabel(
            "📋  Equivalent to git_init.sh\n"
            "Runs git init → git add . → git commit → git branch -M main\n"
            "in every sub-directory of the selected folder."
        )
        info_lbl.setObjectName("infoText")
        info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(info_lbl)
        layout.addWidget(info)

        # Projects dir
        self.projects_row = FolderInputRow(
            "Projects Directory",
            "e.g. " + DEFAULT_PROJECTS_DIR,
            default_text=DEFAULT_PROJECTS_DIR,
            show_cwd_btn=True,
        )
        self.projects_row.browse_btn.clicked.connect(
            lambda: self._browse(self.projects_row.input)
        )
        layout.addWidget(self.projects_row)

        # Mode toggle
        self.single_chk = QCheckBox(
            "Run on this folder directly (treat selected folder as the project, not its sub-folders)"
        )
        self.single_chk.setObjectName("modeCheck")
        layout.addWidget(self.single_chk)

        # Run button — label changes with checkbox
        self.run_btn = QPushButton("⚡  Run git init on All Sub-folders")
        self.run_btn.setObjectName("extractBtn")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self.single_chk.toggled.connect(self._update_btn_label)

        self.progress_bar = make_progress_bar()
        layout.addWidget(self.progress_bar)

        layout.addWidget(SectionLabel("Output Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)

    def _update_btn_label(self, single: bool):
        if single:
            self.run_btn.setText("⚡  Run git init on This Folder")
        else:
            self.run_btn.setText("⚡  Run git init on All Sub-folders")

    def _browse(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            line_edit.setText(folder)

    def _run(self):
        projects_dir = self.projects_row.input.text().strip()
        if not projects_dir:
            QMessageBox.warning(self, "Warning", "Please set the Projects Directory.")
            return

        single = self.single_chk.isChecked()
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log.clear()

        if single:
            self.log.append(f"🚀  Running git init directly in:\n    {projects_dir}\n")
            self.worker = GitInitWorker(projects_dir, single_folder=True)
        else:
            self.log.append(f"🚀  Running git init in subdirs of:\n    {projects_dir}\n")
            self.worker = GitInitWorker(projects_dir, single_folder=False)

        self.worker.progress_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._done)
        self.worker.start()

    def _done(self):
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        single = self.single_chk.isChecked()
        msg = "git init completed on this folder!" if single else "git init completed for all sub-folders!"
        QMessageBox.information(self, "Done", msg)


# ── Tab 3 — Git Remote ────────────────────────────────────────────────────────

class GitRemoteTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        info = QFrame()
        info.setObjectName("infoBox")
        info_lbl = QLabel(
            "📋  Equivalent to git_remote.sh\n"
            "Adds a remote to every project:\n"
            "http://[USERNAME:TOKEN@]HOST/USERNAME/PROJECT.git\n"
            "Leave Access Token empty to add a remote without embedded credentials."
        )
        info_lbl.setObjectName("infoText")
        info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(info_lbl)
        layout.addWidget(info)

        # Projects dir
        self.projects_row = FolderInputRow(
            "Projects Directory",
            "e.g. " + DEFAULT_PROJECTS_DIR,
            default_text=DEFAULT_PROJECTS_DIR,
            show_cwd_btn=True,
        )
        self.projects_row.browse_btn.clicked.connect(
            lambda: self._browse(self.projects_row.input)
        )
        layout.addWidget(self.projects_row)

        # Remote name
        self.remote_name_row = FieldInputRow(
            "Remote Name", "e.g. local, origin, upstream", DEFAULT_REMOTE_NAME
        )
        layout.addWidget(self.remote_name_row)

        # Username
        self.user_row = FieldInputRow("Forgejo Username", "e.g. my-username", DEFAULT_USERNAME)
        layout.addWidget(self.user_row)

        # Token
        self.token_row = FieldInputRow(
            "Access Token (optional — leave empty for no embedded credentials)",
            "Forgejo API token", DEFAULT_TOKEN,
            echo_mode=QLineEdit.EchoMode.Password
        )
        layout.addWidget(self.token_row)

        # Host
        self.host_row = FieldInputRow("Host", "e.g. localhost:3000", DEFAULT_HOST)
        layout.addWidget(self.host_row)

        # Mode toggle
        self.single_chk = QCheckBox(
            "Run on this folder directly (treat selected folder as the project, not its sub-folders)"
        )
        self.single_chk.setObjectName("modeCheck")
        layout.addWidget(self.single_chk)

        # Run button — label changes with checkbox
        self.run_btn = QPushButton("🔗  Configure Git Remotes for All Sub-folders")
        self.run_btn.setObjectName("infoBtn")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self.single_chk.toggled.connect(self._update_btn_label)

        self.progress_bar = make_progress_bar()
        layout.addWidget(self.progress_bar)

        layout.addWidget(SectionLabel("Output Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)

    def _update_btn_label(self, single: bool):
        if single:
            self.run_btn.setText("🔗  Configure Git Remote for This Folder")
        else:
            self.run_btn.setText("🔗  Configure Git Remotes for All Sub-folders")

    def _browse(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            line_edit.setText(folder)

    def _run(self):
        projects_dir = self.projects_row.input.text().strip()
        remote_name = self.remote_name_row.input.text().strip() or "local"
        username = self.user_row.input.text().strip()
        token = self.token_row.input.text().strip()
        host = self.host_row.input.text().strip()

        # Token is optional — everything else is required.
        if not all([projects_dir, username, host]):
            QMessageBox.warning(
                self, "Warning",
                "Please fill in Projects Directory, Username, and Host.\n"
                "(Access Token may be left empty.)"
            )
            return

        single = self.single_chk.isChecked()
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log.clear()
        self.log.append("🔗  Configuring remotes...\n")

        self.worker = GitRemoteWorker(
            projects_dir, username, token, host,
            remote_name=remote_name, single_folder=single,
        )
        self.worker.progress_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._done)
        self.worker.start()

    def _done(self):
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Done", "Remote configuration complete!")


# ── Tab 4 — Git Push ──────────────────────────────────────────────────────────

class GitPushTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        info = QFrame()
        info.setObjectName("infoBox")
        info_lbl = QLabel(
            "📋  Equivalent to git_push.sh\n"
            "Pushes every project to the chosen remote and branch:\n"
            "git push -u <remote> <branch>"
        )
        info_lbl.setObjectName("infoText")
        info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(info_lbl)
        layout.addWidget(info)

        # Projects dir
        self.projects_row = FolderInputRow(
            "Projects Directory",
            "e.g. " + DEFAULT_PROJECTS_DIR,
            default_text=DEFAULT_PROJECTS_DIR,
        )
        self.projects_row.browse_btn.clicked.connect(
            lambda: self._browse(self.projects_row.input)
        )
        layout.addWidget(self.projects_row)

        # Remote name
        self.remote_name_row = FieldInputRow(
            "Remote Name", "e.g. local, origin, upstream", DEFAULT_REMOTE_NAME
        )
        layout.addWidget(self.remote_name_row)

        # Branch
        self.branch_row = FieldInputRow(
            "Branch", "e.g. main, master", DEFAULT_BRANCH
        )
        layout.addWidget(self.branch_row)

        # Run button — label updates live as remote name changes
        self.run_btn = QPushButton(f"⬆️  Push All Projects to '{DEFAULT_REMOTE_NAME}' Remote")
        self.run_btn.setObjectName("extractBtn")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        self.remote_name_row.input.textChanged.connect(self._update_btn_label)

        self.progress_bar = make_progress_bar()
        layout.addWidget(self.progress_bar)

        layout.addWidget(SectionLabel("Output Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)

    def _update_btn_label(self, text: str):
        name = text.strip() or "local"
        self.run_btn.setText(f"⬆️  Push All Projects to '{name}' Remote")

    def _browse(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            line_edit.setText(folder)

    def _run(self):
        projects_dir = self.projects_row.input.text().strip()
        if not projects_dir:
            QMessageBox.warning(self, "Warning", "Please set the Projects Directory.")
            return

        remote_name = self.remote_name_row.input.text().strip() or "local"
        branch = self.branch_row.input.text().strip() or "main"

        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log.clear()
        self.log.append("⬆️  Pushing repositories...\n")

        self.worker = GitPushWorker(projects_dir, remote_name=remote_name, branch=branch)
        self.worker.progress_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._done)
        self.worker.start()

    def _done(self):
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Done", "Push operation complete!")


# ── Tab — Git Binary Manager ──────────────────────────────────────────────────

class GitBinaryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self.worker = None
        self._build_ui()
        # Auto-detect on startup
        self._auto_detect()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top fixed section (always visible) ───────────────────────────────
        top = QWidget()
        top.setObjectName("tabPage")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(24, 16, 24, 8)
        top_layout.setSpacing(10)

        # Info
        info = QFrame()
        info.setObjectName("infoBox")
        info_lbl = QLabel(
            "📋  Manage the Git binary used by this app.\n"
            "Auto-detect scans common install locations.\n"
            "The path set here is used for ALL git operations in every tab."
        )
        info_lbl.setObjectName("infoText")
        info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(info_lbl)
        top_layout.addWidget(info)

        # Status
        top_layout.addWidget(SectionLabel("Current Git Binary"))
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.status_lbl = QLabel("Not detected yet...")
        self.status_lbl.setObjectName("gitStatusLabel")
        self.status_lbl.setWordWrap(True)
        status_row.addWidget(self.status_lbl, 1)
        detect_btn = QPushButton("🔍  Auto-Detect")
        detect_btn.setObjectName("scanBtn")
        detect_btn.setFixedWidth(130)
        detect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        detect_btn.clicked.connect(self._auto_detect)
        status_row.addWidget(detect_btn)
        top_layout.addLayout(status_row)

        # Manual path
        top_layout.addWidget(SectionLabel("Manual Git Path"))
        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self.path_input = QLineEdit()
        self.path_input.setObjectName("pathInput")
        self.path_input.setPlaceholderText(
            "e.g.  /usr/bin/git  or  C:\\Program Files\\Git\\bin\\git.exe"
        )
        path_row.addWidget(self.path_input, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("browseBtn")
        browse_btn.setFixedWidth(80)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_git)
        path_row.addWidget(browse_btn)
        apply_btn = QPushButton("✅  Apply Path")
        apply_btn.setObjectName("extractBtn")
        apply_btn.setFixedWidth(110)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_path)
        path_row.addWidget(apply_btn)
        top_layout.addLayout(path_row)

        hint = QLabel("💡  Tip: on Linux/Termux run  which git  in a terminal to find the path.")
        hint.setObjectName("sectionLabel")
        hint.setWordWrap(True)
        top_layout.addWidget(hint)

        outer.addWidget(top)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: #2e3347; max-height: 1px; border: none;")
        outer.addWidget(div)

        # ── Scrollable bottom section (install rows + log) ────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        container = QWidget()
        container.setObjectName("tabPage")
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 12, 24, 16)
        layout.setSpacing(10)

        layout.addWidget(SectionLabel("Install / Update Git"))

        # Show who we're running as
        if platform.system() != "Windows":
            if _is_root():
                _user_badge = "🟢  Running as root — sudo not required"
            else:
                _user_badge = "🔵  Running as non-root user — sudo password required for system packages"
            badge_lbl = QLabel(_user_badge)
            badge_lbl.setObjectName("sectionLabel")
            layout.addWidget(badge_lbl)

        # Sudo password field — only when NOT Windows, NOT Termux, NOT root
        _show_sudo = (
            platform.system() != "Windows"
            and not _is_termux()
            and not _is_root()
        )

        if _show_sudo:
            sudo_frame = QFrame()
            sudo_frame.setObjectName("infoBox")
            sudo_layout = QVBoxLayout(sudo_frame)
            sudo_layout.setContentsMargins(10, 8, 10, 8)
            sudo_layout.setSpacing(4)
            sudo_lbl = QLabel("🔑  Sudo Password  (required for apt/dnf/pacman)")
            sudo_lbl.setObjectName("sectionLabel")
            sudo_lbl.setWordWrap(True)
            sudo_layout.addWidget(sudo_lbl)
            self.sudo_input = QLineEdit()
            self.sudo_input.setObjectName("pathInput")
            self.sudo_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.sudo_input.setPlaceholderText("Enter sudo password…")
            sudo_layout.addWidget(self.sudo_input)
            layout.addWidget(sudo_frame)
        else:
            self.sudo_input = None

        self.install_cmds = get_install_commands()
        for entry in self.install_cmds:
            row = QFrame()
            row.setObjectName("installRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(10)
            lbl = QLabel(f"<b>{entry['label']}</b><br><small>{entry['note']}</small>")
            lbl.setObjectName("installLabel")
            lbl.setWordWrap(True)
            rl.addWidget(lbl, 1)
            btn = QPushButton("▶  Run")
            btn.setObjectName("infoBtn")
            btn.setFixedWidth(80)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, e=entry: self._run_install(e))
            rl.addWidget(btn)
            layout.addWidget(row)

        self.progress_bar = make_progress_bar()
        layout.addWidget(self.progress_bar)

        self.cancel_btn = QPushButton("⛔  Cancel")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_install)
        layout.addWidget(self.cancel_btn)

        layout.addWidget(SectionLabel("Output Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)
        layout.addStretch()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _auto_detect(self):
        path = auto_detect_git()
        if path:
            set_git_path(path)
            self.path_input.setText(path)
            version = get_git_version(path) or "version unknown"
            self.status_lbl.setText(f"✅  {path}\n    {version}")
            self.status_lbl.setStyleSheet("color: #4ade80; font-size: 13px;")
        else:
            self.status_lbl.setText(
                "❌  Git not found on PATH or common locations.\n"
                "    Please install git or set the path manually below."
            )
            self.status_lbl.setStyleSheet("color: #f87171; font-size: 13px;")

    def _browse_git(self):
        if platform.system() == "Windows":
            filt = "Executable (*.exe);;All files (*)"
        else:
            filt = "All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select git binary", "", filt)
        if path:
            self.path_input.setText(path)

    def _apply_path(self):
        path = self.path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Warning", "Please enter or browse for a git binary path.")
            return
        if not os.path.isfile(path):
            QMessageBox.warning(self, "Warning", f"File not found:\n{path}")
            return
        if not os.access(path, os.X_OK):
            QMessageBox.warning(self, "Warning", f"File is not executable:\n{path}")
            return

        set_git_path(path)
        version = get_git_version(path) or "version unknown"
        self.status_lbl.setText(f"✅  {path}\n    {version}")
        self.status_lbl.setStyleSheet("color: #4ade80; font-size: 13px;")
        QMessageBox.information(self, "Applied",
                                f"Git path set to:\n{path}\n\n{version}")

    def _run_install(self, entry: dict):
        if not entry["cmd"]:
            QMessageBox.information(self, "Info", entry["note"])
            return

        sudo_pwd = None
        if self.sudo_input is not None:
            sudo_pwd = self.sudo_input.text() or None

        self.progress_bar.setVisible(True)
        self.cancel_btn.setVisible(True)
        self.log.clear()
        self.log.append(
            f"📦  {entry['label']}\n"
            f"    {entry['note']}\n{'─'*50}\n"
        )

        self.worker = GitBinaryWorker(
            entry["cmd"],
            needs_sudo=entry.get("needs_admin", False),
            sudo_password=sudo_pwd,
        )
        self.worker.progress_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._install_done)
        self.worker.start()

    def _cancel_install(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)

    def _install_done(self):
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._auto_detect()
        self.log.append("\n🔍  Re-detecting git binary after install...")


# ── Tab 5 — Source Clone Manager ─────────────────────────────────────────────

class SourceCloneTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("tabPage")
        self.clone_worker = None
        self.delete_worker = None
        self._build_ui()

    def _build_ui(self):
        # Outer layout holds scroll area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        container.setObjectName("tabPage")
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        info = QFrame()
        info.setObjectName("infoBox")
        self._info_lbl = QLabel()
        self._info_lbl.setObjectName("infoText")
        self._info_lbl.setWordWrap(True)
        QVBoxLayout(info).addWidget(self._info_lbl)
        layout.addWidget(info)

        # ── Mode toggle ───────────────────────────────────────────────
        self.chk_local = QCheckBox(
            "📁  Local mode — clone directly from the bare .git folder (no HTTP, no credentials)"
        )
        self.chk_local.setObjectName("modeCheck")
        self.chk_local.toggled.connect(self._on_mode_changed)
        layout.addWidget(self.chk_local)

        # Bare repo source
        self.src_row = FolderInputRow(
            "Source (bare .git repos)",
            "Path to Forgejo bare repos...",
            default_text=DEFAULT_BARE_REPO_DIR,
        )
        self.src_row.browse_btn.clicked.connect(lambda: self._browse(self.src_row.input))
        layout.addWidget(self.src_row)

        # Clone destination
        self.desktop_row = FolderInputRow(
            "Clone Destination",
            "Where to place -source-code folders...",
            default_text=DEFAULT_DESKTOP_DIR,
        )
        self.desktop_row.browse_btn.clicked.connect(lambda: self._browse(self.desktop_row.input))
        layout.addWidget(self.desktop_row)

        # Credentials (hidden in local mode)
        self.user_row = FieldInputRow("Username", "e.g. my-username", DEFAULT_USERNAME)
        layout.addWidget(self.user_row)

        self.token_row = FieldInputRow(
            "Token (optional — leave empty for no embedded credentials)",
            "Forgejo API token", DEFAULT_TOKEN,
            echo_mode=QLineEdit.EchoMode.Password
        )
        layout.addWidget(self.token_row)

        self.host_row = FieldInputRow("Host", "e.g. localhost:3000", DEFAULT_HOST)
        layout.addWidget(self.host_row)

        # initialise info label and credential visibility
        self._on_mode_changed(False)

        # Scan button
        scan_btn = QPushButton("🔍  Scan Repositories")
        scan_btn.setObjectName("scanBtn")
        scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_btn.clicked.connect(self._scan)
        layout.addWidget(scan_btn)

        # Repo list
        # Repo list header row with Select All
        repo_header = QHBoxLayout()
        repo_header.addWidget(SectionLabel(
            "Repositories  ·  ✅ = Already Cloned  ·  Ctrl+Click multi-select"
        ))
        repo_header.addStretch()
        self.btn_select_all_repos = QPushButton("Select All")
        self.btn_select_all_repos.setFixedHeight(34)
        self.btn_select_all_repos.setContentsMargins(8, 0, 8, 0)
        self.btn_select_all_repos.clicked.connect(lambda: self.repo_list.selectAll())
        self.btn_deselect_repos = QPushButton("Deselect")
        self.btn_deselect_repos.setFixedHeight(34)
        self.btn_deselect_repos.setContentsMargins(8, 0, 8, 0)
        self.btn_deselect_repos.clicked.connect(lambda: self.repo_list.clearSelection())
        repo_header.addWidget(self.btn_select_all_repos)
        repo_header.addWidget(self.btn_deselect_repos)
        layout.addLayout(repo_header)

        self.repo_list = QListWidget()
        self.repo_list.setObjectName("repoList")
        self.repo_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.repo_list.setMinimumHeight(110)
        layout.addWidget(self.repo_list)

        # Existing clones list header row with Select All
        clone_header = QHBoxLayout()
        clone_header.addWidget(SectionLabel(
            "Existing -source-code Clones  ·  Select to Remove"
        ))
        clone_header.addStretch()
        self.btn_select_all_clones = QPushButton("Select All")
        self.btn_select_all_clones.setFixedHeight(34)
        self.btn_select_all_clones.setContentsMargins(8, 0, 8, 0)
        self.btn_select_all_clones.clicked.connect(lambda: self.clone_list.selectAll())
        self.btn_deselect_clones = QPushButton("Deselect")
        self.btn_deselect_clones.setFixedHeight(34)
        self.btn_deselect_clones.setContentsMargins(8, 0, 8, 0)
        self.btn_deselect_clones.clicked.connect(lambda: self.clone_list.clearSelection())
        clone_header.addWidget(self.btn_select_all_clones)
        clone_header.addWidget(self.btn_deselect_clones)
        layout.addLayout(clone_header)

        self.clone_list = QListWidget()
        self.clone_list.setObjectName("repoList")
        self.clone_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.clone_list.setMinimumHeight(90)
        layout.addWidget(self.clone_list)

        # Suffix toggle
        self.chk_suffix = QCheckBox(
            "Append '-source-code' to cloned folder names  (e.g. api-forge-source-code)"
        )
        self.chk_suffix.setObjectName("modeCheck")
        self.chk_suffix.setChecked(True)
        layout.addWidget(self.chk_suffix)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.clone_btn = QPushButton("📥  Clone Selected Repos")
        self.clone_btn.setObjectName("extractBtn")
        self.clone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clone_btn.clicked.connect(self._start_clone)
        btn_row.addWidget(self.clone_btn)

        self.delete_btn = QPushButton("🗑️  Remove Selected Clones")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._start_delete)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

        self.progress_bar = make_progress_bar()
        layout.addWidget(self.progress_bar)

        layout.addWidget(SectionLabel("Output Log"))
        self.log = make_log_area()
        layout.addWidget(self.log)
        layout.addStretch()

    def _on_mode_changed(self, local: bool):
        for row in (self.user_row, self.token_row, self.host_row):
            row.setVisible(not local)
        if local:
            self._info_lbl.setText(
                "📋  Local mode — clones bare .git repos directly from the source folder.\n"
                "Command:  git clone /path/to/project.git project-source-code\n"
                "No HTTP, no username/token/host required.\n"
                "To remove a clone, select it below and click 'Remove Selected Clones'."
            )
        else:
            self._info_lbl.setText(
                "📋  Remote mode — clones via HTTP from a Forgejo/Gitea instance.\n"
                "Command:  git clone http://[USER:TOKEN@]HOST/USER/PROJECT.git project-source-code\n"
                "Token is optional — leave empty to clone without embedded credentials.\n"
                "To remove a clone, select it below and click 'Remove Selected Clones'."
            )

    def _browse(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            line_edit.setText(folder)

    def _scan(self):
        self.repo_list.clear()
        self.clone_list.clear()

        src = self.src_row.input.text().strip()
        desktop = self.desktop_row.input.text().strip()

        if not os.path.isdir(src):
            QMessageBox.warning(self, "Warning", "Source folder not found!")
            return

        repos = sorted(
            d for d in os.listdir(src)
            if os.path.isdir(os.path.join(src, d)) and d.endswith(".git")
        )

        use_suffix = self.chk_suffix.isChecked()

        for repo in repos:
            project = repo.removesuffix(".git")
            folder_name = f"{project}-source-code" if use_suffix else project
            clone_path = os.path.join(desktop, folder_name)
            already = os.path.isdir(clone_path)
            display = f"{'✅' if already else '⬜'}  {repo}"
            self.repo_list.addItem(display)

        if os.path.isdir(desktop):
            if use_suffix:
                clones = sorted(
                    d for d in os.listdir(desktop)
                    if os.path.isdir(os.path.join(desktop, d)) and d.endswith("-source-code")
                )
            else:
                # Match folders whose name corresponds to a bare repo in src
                repo_names = {r.removesuffix(".git") for r in repos}
                clones = sorted(
                    d for d in os.listdir(desktop)
                    if os.path.isdir(os.path.join(desktop, d)) and d in repo_names
                )
            self.clone_list.addItems(clones)

        self.log.append(
            f"✅  Found {len(repos)} repo(s), "
            f"{self.clone_list.count()} existing clone(s)."
        )

    def _start_clone(self):
        selected = self.repo_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select at least one repository to clone.")
            return

        src     = self.src_row.input.text().strip()
        desktop = self.desktop_row.input.text().strip()
        local   = self.chk_local.isChecked()

        if not src or not desktop:
            QMessageBox.warning(self, "Warning", "Please set Source and Clone Destination.")
            return

        username = self.user_row.input.text().strip()
        token    = self.token_row.input.text().strip()
        host     = self.host_row.input.text().strip()

        if not local and not all([username, host]):
            QMessageBox.warning(
                self, "Warning",
                "Remote mode requires Username and Host.\n"
                "(Token may be left empty.)"
            )
            return

        repos = []
        for item in selected:
            text = item.text()
            repo_name = text.split("  ", 1)[1].strip() if "  " in text else text.strip()
            repos.append(repo_name)

        self.clone_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log.clear()
        mode_label = "local path" if local else "HTTP remote"
        self.log.append(f"📥  Cloning {len(repos)} repo(s) via {mode_label}...\n")

        self.clone_worker = CloneWorker(
            repos, src, desktop, username, token, host,
            local_mode=local,
            add_suffix=self.chk_suffix.isChecked(),
        )
        self.clone_worker.progress_signal.connect(self.log.append)
        self.clone_worker.finished_signal.connect(self._clone_done)
        self.clone_worker.start()

    def _clone_done(self):
        self.clone_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Done", "Clone operation complete!")
        self._scan()

    def _start_delete(self):
        selected = self.clone_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select at least one clone to remove.")
            return

        desktop = self.desktop_row.input.text().strip()
        folders = [item.text() for item in selected]

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"The following {len(folders)} folder(s) will be permanently deleted:\n\n"
            + "\n".join(folders)
            + "\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.clone_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log.clear()
        self.log.append(f"🗑️  Removing {len(folders)} clone(s)...\n")

        self.delete_worker = DeleteCloneWorker(folders, desktop)
        self.delete_worker.progress_signal.connect(self.log.append)
        self.delete_worker.finished_signal.connect(self._delete_done)
        self.delete_worker.start()

    def _delete_done(self):
        self.clone_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Done", "Selected clones removed!")
        self._scan()


# ── Main Window ───────────────────────────────────────────────────────────────

class ForgeGitManagerApp(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("Forge Git Manager")
        self.setMinimumSize(700, 560)
        self.resize(900, 700)
        self.setObjectName("mainWindow")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(60)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        title = QLabel("⬡  Forge Git Manager")
        title.setObjectName("appTitle")

        version = QLabel("v2.0.0")
        version.setObjectName("versionBadge")

        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(version)
        root.addWidget(header)

        # ── Tab Widget ────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tabs.addTab(GitBinaryTab(),    "⚙️  Git Binary")
        self.tabs.addTab(ExtractorTab(),    "📦  Extractor")
        self.tabs.addTab(GitignoreTab(),    "📄  Gitignore")
        self.tabs.addTab(GitInitTab(),      "🔧  Git Init")
        self.tabs.addTab(GitRemoteTab(),    "🔗  Git Remote")
        self.tabs.addTab(GitPushTab(),      "⬆️  Git Push")
        self.tabs.addTab(SourceCloneTab(),  "📥  Source Clone")

        root.addWidget(self.tabs, 1)

        # ── Status Bar ────────────────────────────────────────────
        status = QFrame()
        status.setObjectName("statusBar")
        status.setFixedHeight(36)
        sl = QHBoxLayout(status)
        sl.setContentsMargins(24, 0, 24, 0)

        status_lbl = QLabel("Forge Git Manager — Ready")
        status_lbl.setObjectName("statusLabel")
        sl.addWidget(status_lbl)
        sl.addStretch()

        hint = QLabel("Extractor · Git Init · Git Remote · Git Push · Source Clone")
        hint.setObjectName("statusLabel")
        sl.addWidget(hint)

        root.addWidget(status)


def main():
    # High-DPI support — must be set before QApplication
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    apply_theme(app)
    app.setStyleSheet(STYLESHEET)

    window = ForgeGitManagerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
