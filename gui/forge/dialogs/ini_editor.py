# gui/dialogs/ini_editor.py
"""app.ini syntax-highlighted editor dialog."""

from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import (
    QColor, QFont, QSyntaxHighlighter, QTextCharFormat,
)
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from forge.constants import (
    ACCENT, BG_MANTLE, BG_OVERLAY, BG_SURFACE,
    FG_SUBTLE, FG_TEXT, GREEN, MAUVE, RED, TEAL, YELLOW,
)


class IniSyntaxHighlighter(QSyntaxHighlighter):
    """Lightweight syntax highlighter for app.ini (Gitea/Forgejo config).

    Highlights:
      - [section] headers
      - key names (before '=')
      - '=' separators
      - values: booleans, numbers, and generic strings get distinct colors
      - comments (';' or '#')
    Warnings (underlined in a warning color):
      - duplicate [section] headers
      - lines that look like 'key value' with no '=' (likely a typo)
      - unmatched '[' / ']' on a line claiming to be a section header
    """

    def __init__(self, document):
        super().__init__(document)

        self._fmt_section = self._fmt(MAUVE, bold=True)
        self._fmt_key     = self._fmt(TEAL)
        self._fmt_op      = self._fmt(FG_SUBTLE)
        self._fmt_bool    = self._fmt(GREEN, bold=True)
        self._fmt_number  = self._fmt(YELLOW)
        self._fmt_value   = self._fmt(FG_TEXT)
        self._fmt_comment = self._fmt(FG_SUBTLE, italic=True)
        self._fmt_warning = self._fmt(RED, underline=True)

        self._re_section = QRegularExpression(r"^\s*\[[^\]]*\]\s*$")
        self._re_kv      = QRegularExpression(r"^(\s*)([^=;#\[][^=]*?)(\s*=\s*)(.*)$")
        self._re_comment = QRegularExpression(r"^\s*[;#].*$")
        self._re_bool    = QRegularExpression(
            r"^(true|false)$",
            QRegularExpression.PatternOption.CaseInsensitiveOption,
        )
        self._re_number = QRegularExpression(r"^-?\d+(\.\d+)?$")

        self._seen_sections: set[str] = set()

    @staticmethod
    def _fmt(
        color: str,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
    ) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            f.setFontWeight(QFont.Weight.Bold)
        if italic:
            f.setFontItalic(True)
        if underline:
            f.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            f.setUnderlineColor(QColor(color))
        return f

    def highlightBlock(self, text: str):
        # Reset the duplicate-section tracker at the start of a fresh pass
        # over the whole document (block 0).
        if self.currentBlock().blockNumber() == 0:
            self._seen_sections = set()

        stripped = text.strip()
        if not stripped:
            return

        # Comments
        if self._re_comment.match(text).hasMatch():
            self.setFormat(0, len(text), self._fmt_comment)
            return

        # Section headers: [name]
        if stripped.startswith("["):
            if self._re_section.match(text).hasMatch():
                self.setFormat(0, len(text), self._fmt_section)
                name = stripped.strip("[]").strip()
                if name in self._seen_sections:
                    self.setFormat(0, len(text), self._fmt_warning)
                else:
                    self._seen_sections.add(name)
            else:
                # Looks like a section header but malformed (missing ']' etc.)
                self.setFormat(0, len(text), self._fmt_warning)
            return

        # key = value
        m = self._re_kv.match(text)
        if m.hasMatch():
            self.setFormat(m.capturedStart(2), m.capturedLength(2), self._fmt_key)
            self.setFormat(m.capturedStart(3), m.capturedLength(3), self._fmt_op)

            value = m.captured(4).strip()
            if self._re_bool.match(value).hasMatch():
                fmt = self._fmt_bool
            elif self._re_number.match(value).hasMatch():
                fmt = self._fmt_number
            else:
                fmt = self._fmt_value
            self.setFormat(m.capturedStart(4), m.capturedLength(4), fmt)
            return

        # Anything else non-blank with no '=' — likely a typo'd key/value line.
        self.setFormat(0, len(text), self._fmt_warning)


class IniEditorDialog(QDialog):
    """Full-screen-ish popup editor for app.ini with syntax highlighting
    and a status bar showing line count and any detected warnings
    (duplicate sections, malformed lines).
    """

    def __init__(self, content: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit app.ini")
        self.setModal(True)
        self.resize(900, 700)
        self.setMinimumSize(560, 400)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        hint = QLabel(
            "💡 Syntax: [section] headers (mauve), keys (teal), "
            "true/false (green), numbers (yellow), comments (italic). "
            "Lines underlined in red look malformed (missing '=', duplicate "
            "section, or unclosed '[...]')."
        )
        hint.setStyleSheet(f"font-size: 18px; color: {FG_SUBTLE};")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(content)
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        mono = QFont("JetBrains Mono", 22)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.text_edit.setFont(mono)
        self.text_edit.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {BG_MANTLE}; color: {FG_TEXT}; "
            f"border: 1px solid {BG_OVERLAY}; border-radius: 4px; padding: 6px; }}"
        )
        self.highlighter = IniSyntaxHighlighter(self.text_edit.document())
        lay.addWidget(self.text_edit, stretch=1)

        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"font-size: 18px; color: {FG_SUBTLE};")
        lay.addWidget(self.status_label)
        self.text_edit.textChanged.connect(self._update_status)
        self._update_status()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(44)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("💾  Save")
        btn_save.setFixedHeight(44)
        btn_save.setObjectName("btn_setup")   # reuse the mauve accent style
        btn_save.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        lay.addLayout(btn_row)

    # ── private ───────────────────────────────────────────────────────

    def _update_status(self):
        text   = self.text_edit.toPlainText()
        lines  = text.split("\n")
        n_lines = len(lines)

        sections: dict[str, int] = {}
        warnings = 0
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith((";", "#")):
                continue
            if stripped.startswith("["):
                if stripped.endswith("]") and len(stripped) >= 2:
                    name = stripped.strip("[]").strip()
                    if name in sections:
                        warnings += 1
                    sections[name] = i
                else:
                    warnings += 1
            elif "=" not in stripped:
                warnings += 1

        msg = f"{n_lines} lines · {len(sections)} sections"
        if warnings:
            msg += f"  ·  ⚠ {warnings} possible issue(s) — check underlined lines"
            self.status_label.setStyleSheet(f"font-size: 18px; color: {RED};")
        else:
            self.status_label.setStyleSheet(f"font-size: 18px; color: {FG_SUBTLE};")
        self.status_label.setText(msg)
