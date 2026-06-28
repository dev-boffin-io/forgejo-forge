# gui/constants.py
"""App-wide constants: name, version, Catppuccin Mocha colors, and the Qt stylesheet."""

APP_NAME    = "forgejo-forge"
APP_VERSION = "1.0.0"
BINARY_NAME = "forgejo-forge"

# ── Catppuccin Mocha palette ─────────────────────────────────────────────────
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

# ── Qt stylesheet ─────────────────────────────────────────────────────────────
STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {FG_TEXT};
    font-family: 'JetBrains Mono', 'Fira Code', 'Monospace';
    font-size: 26px;
}}
QGroupBox {{
    border: 1px solid {BG_OVERLAY};
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 12px;
    color: {ACCENT};
    font-weight: bold;
    font-size: 24px;
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
    font-size: 24px;
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
    font-size: 24px;
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
QPushButton#btn_runner_install  {{ border-color: {GREEN};  color: {GREEN}; }}
QPushButton#btn_runner_install:hover  {{ background-color: {GREEN};  color: {BG_BASE}; }}
QPushButton#btn_runner_register {{ border-color: {MAUVE};  color: {MAUVE}; }}
QPushButton#btn_runner_register:hover {{ background-color: {MAUVE};  color: {BG_BASE}; }}
QPushButton#btn_runner_start    {{ border-color: {GREEN};  color: {GREEN}; }}
QPushButton#btn_runner_start:hover    {{ background-color: {GREEN};  color: {BG_BASE}; }}
QPushButton#btn_runner_stop     {{ border-color: {RED};    color: {RED}; }}
QPushButton#btn_runner_stop:hover     {{ background-color: {RED};    color: {BG_BASE}; }}
QPushButton#btn_runner_status   {{ border-color: {TEAL};   color: {TEAL}; }}
QPushButton#btn_runner_status:hover   {{ background-color: {TEAL};   color: {BG_BASE}; }}
QPushButton#btn_runner_uninstall {{ border-color: {RED};   color: {RED}; }}
QPushButton#btn_runner_uninstall:hover {{ background-color: {RED};  color: {BG_BASE}; }}
"""
