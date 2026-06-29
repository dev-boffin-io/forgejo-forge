# gui/forge/tabs/git_manager.py
"""Git Manager tab — launches Forge Git Manager as a separate window."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from forge.constants import ACCENT, BG_SURFACE, FG_SUBTLE, FG_TEXT, GREEN


class GitManagerTab(QWidget):
    """⬡ Git Manager tab.

    Shows a brief description of what Forge Git Manager does and a single
    launch button.  The actual window is created lazily on first click and
    re-shown on subsequent clicks (never duplicated).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window = None
        self._build()

    # ── build ─────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Title row
        title = QLabel("⬡  Forge Git Manager")
        title.setStyleSheet(
            f"font-size: 30px; font-weight: bold; color: {ACCENT};"
        )
        lay.addWidget(title)

        # ── Description card
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {BG_SURFACE}; border-radius: 8px; padding: 4px; }}"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 16)
        card_lay.setSpacing(8)

        desc = QLabel(
            "A standalone multi-tab Git workflow GUI designed to work alongside Forgejo.\n\n"
            "Tabs included:\n"
            "  ⚙️  Git Binary   — detect / install git\n"
            "  📦  Extractor    — extract archives into a working tree\n"
            "  📄  Gitignore    — generate .gitignore from templates\n"
            "  🔧  Git Init     — initialise a new repository\n"
            "  🔗  Git Remote   — add / change the remote origin\n"
            "  ⬆️  Git Push     — stage, commit, and push\n"
            "  📥  Source Clone — clone a repository from any remote"
        )
        desc.setStyleSheet(f"font-size: 22px; color: {FG_TEXT}; background: transparent;")
        desc.setWordWrap(True)
        card_lay.addWidget(desc)
        lay.addWidget(card)

        # ── Launch button
        btn_row = QHBoxLayout()
        self.btn_launch = QPushButton("⬡  Open Git Manager")
        self.btn_launch.setFixedHeight(56)
        self.btn_launch.setStyleSheet(
            f"QPushButton {{"
            f"  background: {BG_SURFACE}; border: 2px solid {GREEN};"
            f"  border-radius: 6px; color: {GREEN};"
            f"  font-size: 26px; font-weight: bold; padding: 0 28px;"
            f"}}"
            f"QPushButton:hover {{ background: {GREEN}; color: #1e1e2e; }}"
            f"QPushButton:pressed {{ opacity: 0.85; }}"
        )
        self.btn_launch.clicked.connect(self._launch)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_launch)
        lay.addLayout(btn_row)

        hint = QLabel("Opens as a separate window — you can keep using forgejo-forge alongside it.")
        hint.setStyleSheet(f"font-size: 20px; color: {FG_SUBTLE};")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(hint)

        lay.addStretch()

    # ── slot ──────────────────────────────────────────────────────────

    def _launch(self):
        try:
            from forge_git_manager.app import ForgeGitManagerApp
            from forge_git_manager.theme import STYLESHEET
        except ImportError as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Import error",
                f"forge_git_manager package not found:\n{e}\n\n"
                "Make sure gui/forge_git_manager/ exists.",
            )
            return

        if self._window is None:
            from PyQt6.QtWidgets import QApplication
            self._window = ForgeGitManagerApp()
            # Apply Git Manager's own stylesheet scoped to its window only —
            # avoids overriding forgejo-forge's Catppuccin Mocha QApplication stylesheet.
            self._window.setStyleSheet(STYLESHEET)
            # Screen-aware sizing
            screen = QApplication.primaryScreen().availableGeometry()
            w = min(1100, int(screen.width()  * 0.75))
            h = min(800,  int(screen.height() * 0.80))
            self._window.resize(w, h)
            self._window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self._window.destroyed.connect(self._on_window_closed)

        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _on_window_closed(self):
        self._window = None
