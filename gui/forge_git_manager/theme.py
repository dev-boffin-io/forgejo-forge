"""
Dark "Forge" theme — slate-900 base, amber accent, monospace log.
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor

# ── Palette tokens ────────────────────────────────────────────────────────────
BG_BASE      = "#0f1117"
BG_SURFACE   = "#1a1d27"
BG_ELEVATED  = "#22263a"
BG_HEADER    = "#0d0f18"
BG_STATUS    = "#0d0f18"

BORDER       = "#2e3347"
BORDER_FOCUS = "#f59e0b"

TEXT_PRIMARY = "#e8eaf6"
TEXT_MUTED   = "#6b7280"
TEXT_ACCENT  = "#f59e0b"

ACCENT_BTN   = "#f59e0b"
EXTRACT_BTN  = "#16a34a"
EXTRACT_HOVER= "#15803d"
DANGER_BTN   = "#dc2626"
DANGER_HOVER = "#b91c1c"
INFO_BTN     = "#2563eb"
INFO_HOVER   = "#1d4ed8"

PROGRESS_BAR = "#f59e0b"
SELECTION_BG = "#2c3a5e"
SELECTION_FG = "#e8eaf6"


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(BG_BASE))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base,            QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_SURFACE))
    palette.setColor(QPalette.ColorRole.Text,            QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button,          QColor(BG_SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(SELECTION_BG))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(SELECTION_FG))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    app.setPalette(palette)


STYLESHEET = f"""
/* ── Root window ────────────────────────────────────────── */
QWidget#mainWindow {{
    background: {BG_BASE};
    font-family: 'Inter', 'Segoe UI', 'SF Pro Display', sans-serif;
    font-size: 14px;
    color: {TEXT_PRIMARY};
}}

/* ── Tab Widget ─────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: {BG_BASE};
}}
QTabWidget::tab-bar {{
    left: 0px;
}}
QTabBar {{
    background: {BG_HEADER};
    border-bottom: 1px solid {BORDER};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    font-size: 13px;
    font-weight: 600;
    padding: 10px 20px;
    border: none;
    border-bottom: 3px solid transparent;
    letter-spacing: 0.3px;
    min-width: 100px;
}}
QTabBar::tab:selected {{
    color: {TEXT_ACCENT};
    border-bottom: 3px solid {TEXT_ACCENT};
    background: rgba(245, 158, 11, 0.06);
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
    background: rgba(255,255,255,0.04);
}}

/* ── Header bar ─────────────────────────────────────────── */
QFrame#headerBar {{
    background: {BG_HEADER};
    border-bottom: 1px solid {BORDER};
}}
QLabel#appTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT_ACCENT};
    letter-spacing: 0.5px;
}}
QLabel#versionBadge {{
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_MUTED};
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 3px 10px;
}}

/* ── Body ───────────────────────────────────────────────── */
QWidget#tabPage {{
    background: {BG_BASE};
}}

/* ── Section labels ─────────────────────────────────────── */
QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 700;
    color: {TEXT_MUTED};
    letter-spacing: 1.2px;
    margin-bottom: 2px;
}}

/* ── Info box ───────────────────────────────────────────── */
QFrame#infoBox {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-left: 3px solid {TEXT_ACCENT};
    border-radius: 8px;
}}
QLabel#infoText {{
    font-size: 12px;
    color: {TEXT_MUTED};
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    padding: 10px 14px;
    line-height: 1.5;
}}

/* ── Path inputs ────────────────────────────────────────── */
QLineEdit#pathInput {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    selection-background-color: {SELECTION_BG};
}}
QLineEdit#pathInput:focus {{
    border-color: {BORDER_FOCUS};
}}

/* ── Browse button ──────────────────────────────────────── */
QPushButton#browseBtn {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    padding: 8px 16px;
    min-width: 80px;
}}
QPushButton#browseBtn:hover {{
    border-color: {BORDER_FOCUS};
    color: {TEXT_ACCENT};
}}
QPushButton#browseBtn:pressed {{
    background: {BG_SURFACE};
}}

/* ── Gitignore template toggle buttons ──────────────────── */
QPushButton#tmplBtnOff {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
    padding: 8px 10px;
    text-align: left;
}}
QPushButton#tmplBtnOff:hover {{
    border-color: {BORDER_FOCUS};
    color: {TEXT_PRIMARY};
}}
QPushButton#tmplBtnOn {{
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid {ACCENT_BTN};
    border-radius: 6px;
    color: {TEXT_ACCENT};
    font-size: 12px;
    font-weight: 700;
    padding: 8px 10px;
    text-align: left;
}}
QPushButton#tmplBtnOn:hover {{
    background: rgba(245, 158, 11, 0.22);
}}

/* ── Git Binary tab — install rows ──────────────────────── */
QFrame#installRow {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QLabel#installLabel {{
    font-size: 13px;
    color: {TEXT_PRIMARY};
    line-height: 1.5;
}}
QLabel#gitStatusLabel {{
    font-size: 13px;
    color: {TEXT_MUTED};
    padding: 6px 0;
}}

/* ── Mode checkbox ───────────────────────────────────────── */
QCheckBox#modeCheck {{
    color: {TEXT_MUTED};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox#modeCheck:hover {{
    color: {TEXT_PRIMARY};
}}
QCheckBox#modeCheck::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_ELEVATED};
}}
QCheckBox#modeCheck::indicator:checked {{
    background: {ACCENT_BTN};
    border-color: {ACCENT_BTN};
}}

/* ── Use Current Dir button ─────────────────────────────── */
QPushButton#cwdBtn {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_ACCENT};
    font-size: 12px;
    font-weight: 500;
    padding: 8px 10px;
}}
QPushButton#cwdBtn:hover {{
    border-color: {BORDER_FOCUS};
    background: rgba(245, 158, 11, 0.08);
}}
QPushButton#cwdBtn:pressed {{
    background: rgba(245, 158, 11, 0.15);
}}

/* ── Scan / primary outline button ─────────────────────── */
QPushButton#scanBtn {{
    background: transparent;
    border: 1px solid {ACCENT_BTN};
    border-radius: 6px;
    color: {ACCENT_BTN};
    font-size: 13px;
    font-weight: 600;
    padding: 10px 20px;
}}
QPushButton#scanBtn:hover {{
    background: rgba(245, 158, 11, 0.10);
}}
QPushButton#scanBtn:pressed {{
    background: rgba(245, 158, 11, 0.18);
}}

/* ── Repository list ────────────────────────────────────── */
QListWidget#repoList {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    outline: none;
}}
QListWidget#repoList::item {{
    padding: 6px 12px;
    border-radius: 4px;
    margin: 1px 0;
}}
QListWidget#repoList::item:selected {{
    background: {SELECTION_BG};
    color: {SELECTION_FG};
}}
QListWidget#repoList::item:hover:!selected {{
    background: rgba(255,255,255,0.04);
}}

/* ── Extract / green action button ─────────────────────── */
QPushButton#extractBtn {{
    background: {EXTRACT_BTN};
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 20px;
}}
QPushButton#extractBtn:hover {{
    background: {EXTRACT_HOVER};
}}
QPushButton#extractBtn:pressed {{
    background: #166534;
}}
QPushButton#extractBtn:disabled {{
    background: #1f4a2c;
    color: #4b6e54;
}}

/* ── Danger / red action button ─────────────────────────── */
QPushButton#dangerBtn {{
    background: {DANGER_BTN};
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 20px;
}}
QPushButton#dangerBtn:hover {{
    background: {DANGER_HOVER};
}}
QPushButton#dangerBtn:pressed {{
    background: #991b1b;
}}
QPushButton#dangerBtn:disabled {{
    background: #4a1a1a;
    color: #7a4444;
}}

/* ── Info / blue action button ──────────────────────────── */
QPushButton#infoBtn {{
    background: {INFO_BTN};
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 20px;
}}
QPushButton#infoBtn:hover {{
    background: {INFO_HOVER};
}}
QPushButton#infoBtn:pressed {{
    background: #1e3a8a;
}}
QPushButton#infoBtn:disabled {{
    background: #1e2a4a;
    color: #4b5a7a;
}}

/* ── Progress bar ───────────────────────────────────────── */
QProgressBar#progressBar {{
    background: {BG_ELEVATED};
    border: none;
    border-radius: 3px;
}}
QProgressBar#progressBar::chunk {{
    background: {PROGRESS_BAR};
    border-radius: 3px;
}}

/* ── Log area ───────────────────────────────────────────── */
QTextEdit#logArea {{
    background: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    color: #a5d6a7;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: {SELECTION_BG};
}}

/* ── Status bar ─────────────────────────────────────────── */
QFrame#statusBar {{
    background: {BG_STATUS};
    border-top: 1px solid {BORDER};
}}
QLabel#statusLabel {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}

/* ── Scroll bars ────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3e4560;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
}}

/* ── Message boxes ──────────────────────────────────────── */
QMessageBox {{
    background: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QMessageBox QPushButton {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 6px 20px;
    min-width: 80px;
}}
QMessageBox QPushButton:hover {{
    border-color: {BORDER_FOCUS};
}}

/* ── Scroll area background ─────────────────────────────── */
QScrollArea {{
    background: {BG_BASE};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: {BG_BASE};
}}
"""
