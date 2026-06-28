# gui/utils/binary.py
"""Helpers for locating the forgejo-forge and forgejo-main (installer) binaries."""

import os
import platform
import shutil
import sys

from forge.constants import BINARY_NAME


def find_binary(override: str = "") -> str | None:
    """Locate the forgejo-forge binary.

    If *override* is given (set via the Binary tab's path field) that path
    is returned directly after existence + executable checks — no further
    search is done.

    Auto-search order:
    1. PATH  (works after 'make install')
    2. Same directory as this executable  (frozen PyInstaller build:
       both forgejo-forge and forgejo-forge-gui live in bin/)
    3. ./bin/ relative to CWD  (running from source: python3 gui/forgejo-forge.py)
    4. ../bin/ relative to script location
    """
    # 0. Manual override from Binary tab
    if override and os.path.isfile(override) and os.access(override, os.X_OK):
        return override

    # 1. PATH
    if path := shutil.which(BINARY_NAME):
        return path

    # 2. Same dir as the running executable (frozen or not)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidate = os.path.join(exe_dir, BINARY_NAME)
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate

    # 3-4. Relative paths from CWD / script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for base in [os.getcwd(), script_dir, os.path.join(script_dir, "..", "..")]:
        candidate = os.path.join(base, "bin", BINARY_NAME)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def find_installer_binary() -> str | None:
    """Locate the forgejo-main installer binary.

    Search order: PATH → same dir as exe → ./bin/ → ../bin/
    Tries both 'forgejo-main' and platform-specific suffixed variants.
    """
    machine    = platform.machine().lower()
    arch_suffix = "arm64" if machine in ("aarch64", "arm64") else "amd64"
    is_win     = sys.platform == "win32"
    os_tag     = "windows" if is_win else "linux"
    exe_ext    = ".exe" if is_win else ""

    candidates_names = [
        f"forgejo-main{exe_ext}",
        f"forgejo-main-{os_tag}-{arch_suffix}{exe_ext}",
        f"forgejo-main-{arch_suffix}{exe_ext}",
    ]

    # 1. PATH
    for name in candidates_names:
        if path := shutil.which(name):
            return path

    # 2. Same dir as running executable
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for name in candidates_names:
        candidate = os.path.join(exe_dir, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 3-4. bin/ relative to CWD / script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for base in [os.getcwd(), script_dir, os.path.join(script_dir, "..", "..")]:
        for name in candidates_names:
            candidate = os.path.join(base, "bin", name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

    return None


def screen_aware_size(app) -> tuple[int, int]:
    """Return (width, height) capped to 92 % / 85 % of the primary screen."""
    screen = app.primaryScreen().availableGeometry()
    w = min(1280, int(screen.width()  * 0.92))
    h = min(820,  int(screen.height() * 0.85))
    return w, h
