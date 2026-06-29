"""
git_config.py — global Git binary path manager.

All workers import get_git_path() instead of the bare string "git".
Whatever path the user sets in the Git Binary tab is used for every
operation across the entire app.

Cross-platform: Windows, macOS, Linux, Termux, proot-distro.
Python 3.9+ compatible (uses Optional instead of X | None syntax).
"""
from __future__ import annotations

import os
import shutil
import platform
import subprocess
from typing import Optional


# ── Module-level state ────────────────────────────────────────────────────────
_git_path: str = "git"          # default: rely on PATH


def set_git_path(path: str) -> None:
    """Store the resolved git binary path for the whole session."""
    global _git_path
    _git_path = path.strip() or "git"


def get_git_path() -> str:
    """Return the currently configured git binary path."""
    return _git_path


# ── Environment detection ─────────────────────────────────────────────────────

def _is_termux() -> bool:
    """
    True only when running inside real Termux (not proot-distro Debian).
    proot-distro inherits Termux's PATH so shutil.which('pkg') can return
    a result even inside Debian proot. We disambiguate by checking:
      - Termux sets PREFIX to a path containing 'com.termux'
      - proot Debian always has /etc/debian_version
    """
    prefix = os.environ.get("PREFIX", "")
    in_termux_env = (
        "/data/data/com.termux" in prefix
        or os.path.isdir("/data/data/com.termux/files/usr")
    )
    in_debian_proot = os.path.isfile("/etc/debian_version")
    return in_termux_env and not in_debian_proot


def _is_root() -> bool:
    """True when the process is running as root (uid 0). Always False on Windows."""
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined]
    except AttributeError:
        return False  # Windows has no geteuid


# ── Auto-detect git binary ────────────────────────────────────────────────────

def auto_detect_git() -> Optional[str]:
    """
    Return the full path to a usable git binary, or None if not found.
    Checks shutil.which first (honours PATH), then OS-specific locations.
    """
    found = shutil.which("git")
    if found:
        return found

    system = platform.system()

    if system == "Windows":
        candidates = [
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files (x86)\Git\bin\git.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\git.exe"),
            os.path.expandvars(r"%ProgramFiles%\Git\bin\git.exe"),
        ]
    elif system == "Darwin":
        candidates = [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "/opt/homebrew/bin/git",   # Apple-silicon Homebrew
            "/opt/local/bin/git",      # MacPorts
        ]
    else:  # Linux / Termux / proot / BSD
        candidates = [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "/data/data/com.termux/files/usr/bin/git",  # Termux
            "/snap/bin/git",
        ]

    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    return None


def get_git_version(git_path: str = "git") -> Optional[str]:
    """Return 'git version x.y.z' string, or None on failure."""
    try:
        kwargs: dict = dict(capture_output=True, text=True, timeout=10)
        if platform.system() == "Windows":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        result = subprocess.run([git_path, "--version"], **kwargs)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# ── Install command builders ──────────────────────────────────────────────────

def get_install_commands() -> list:
    """
    Return install/upgrade strategies for the current OS and environment.
    Each entry is a dict with: label, cmd (list[str]), note (str), needs_admin (bool).
    Evaluated at call time so root-detection is always accurate.
    """
    system = platform.system()

    # ── Windows ───────────────────────────────────────────────────────────────
    if system == "Windows":
        return [
            {
                "label": "winget  (Windows Package Manager)",
                "cmd": ["winget", "install", "--id", "Git.Git",
                        "-e", "--source", "winget"],
                "note": "Requires Windows 10 1709+ with winget installed.",
                "needs_admin": False,
            },
            {
                "label": "Chocolatey  (choco install git)",
                "cmd": ["choco", "install", "git", "-y"],
                "note": "Requires Chocolatey package manager.",
                "needs_admin": False,  # choco handles its own elevation
            },
            {
                "label": "Scoop  (scoop install git)",
                "cmd": ["scoop", "install", "git"],
                "note": "Requires Scoop package manager.",
                "needs_admin": False,
            },
        ]

    # ── macOS ─────────────────────────────────────────────────────────────────
    elif system == "Darwin":
        return [
            {
                "label": "Homebrew  (brew install git)",
                "cmd": ["brew", "install", "git"],
                "note": "Requires Homebrew — https://brew.sh",
                "needs_admin": False,
            },
            {
                "label": "Homebrew  (brew upgrade git)",
                "cmd": ["brew", "upgrade", "git"],
                "note": "Upgrades an existing Homebrew git.",
                "needs_admin": False,
            },
            {
                "label": "MacPorts  (port install git)",
                "cmd": ["port", "install", "git"],
                "note": "Requires MacPorts — https://www.macports.org",
                "needs_admin": True,
            },
        ]

    # ── Linux / Termux / proot-distro / BSD ───────────────────────────────────
    else:
        termux   = _is_termux()
        as_root  = _is_root()
        managers = []

        # Termux — pkg, no sudo ever
        if termux:
            if shutil.which("pkg"):
                managers += [
                    {
                        "label": "pkg install git  (Termux)",
                        "cmd": ["pkg", "install", "-y", "git"],
                        "note": "Termux package manager — no sudo needed.",
                        "needs_admin": False,
                    },
                    {
                        "label": "pkg upgrade git  (Termux)",
                        "cmd": ["pkg", "upgrade", "-y", "git"],
                        "note": "Upgrade git in Termux — no sudo needed.",
                        "needs_admin": False,
                    },
                ]
            return managers

        # Non-Termux Linux / proot-distro
        # When running as root (proot, Docker, CI) no sudo is needed.
        needs_sudo = not as_root
        root_note  = "Running as root — no sudo needed."
        sudo_note  = "Enter sudo password in the field above before running."

        if shutil.which("apt-get"):
            note = root_note if as_root else sudo_note
            managers += [
                {
                    "label": "apt install git  (Debian / Ubuntu / proot)",
                    "cmd": ["apt-get", "install", "-y", "git"],
                    "note": note,
                    "needs_admin": needs_sudo,
                },
                {
                    "label": "apt upgrade git  (Debian / Ubuntu / proot)",
                    "cmd": ["apt-get", "upgrade", "-y", "git"],
                    "note": note,
                    "needs_admin": needs_sudo,
                },
            ]

        if shutil.which("dnf"):
            note = root_note if as_root else sudo_note
            managers.append({
                "label": "dnf install git  (Fedora / RHEL / CentOS)",
                "cmd": ["dnf", "install", "-y", "git"],
                "note": note,
                "needs_admin": needs_sudo,
            })

        if shutil.which("pacman"):
            note = root_note if as_root else sudo_note
            managers.append({
                "label": "pacman -S git  (Arch Linux / Manjaro)",
                "cmd": ["pacman", "-S", "--noconfirm", "git"],
                "note": note,
                "needs_admin": needs_sudo,
            })

        if shutil.which("zypper"):
            note = root_note if as_root else sudo_note
            managers.append({
                "label": "zypper install git  (openSUSE)",
                "cmd": ["zypper", "install", "-y", "git"],
                "note": note,
                "needs_admin": needs_sudo,
            })

        if shutil.which("apk"):
            note = root_note if as_root else sudo_note
            managers.append({
                "label": "apk add git  (Alpine Linux)",
                "cmd": ["apk", "add", "git"],
                "note": note,
                "needs_admin": needs_sudo,
            })

        if not managers:
            managers.append({
                "label": "No supported package manager detected",
                "cmd": [],
                "note": "Install git manually and set the binary path below.",
                "needs_admin": False,
            })

        return managers
