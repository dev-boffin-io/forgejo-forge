#!/usr/bin/env python3
"""
forgejo-forge GUI
PyQt6 frontend for the forgejo-forge CLI binary.

Entry point — kept at gui/forgejo-forge.py so the Makefile, CI workflows,
and PyInstaller commands need zero changes.

The real code lives in gui/forge/ (the package).
PyInstaller adds gui/ to sys.path automatically when this script is the
entry point, so 'import forge' resolves correctly both from source and
inside a frozen binary.
"""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from forge.constants import APP_NAME
from forge.mainwindow import ForgejoForgeGUI


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
