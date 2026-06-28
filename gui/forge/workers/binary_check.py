# gui/workers/binary_check.py
"""Background worker that detects the installed forgejo/gitea binary
and fetches the latest release version from the upstream API."""

import json
import re
import shutil
import subprocess
import urllib.request
import os

from PyQt6.QtCore import QThread, pyqtSignal


class BinaryCheckWorker(QThread):
    """Detects installed forgejo/gitea binary and fetches latest release version."""

    result = pyqtSignal(dict)   # {binary, path, installed, latest, source, up_to_date}
    error  = pyqtSignal(str)

    SEMVER_RE   = re.compile(r'\d+\.\d+\.\d+')
    FORGEJO_API = "https://codeberg.org/api/v1/repos/forgejo/forgejo/releases/latest"
    GITEA_API   = "https://api.github.com/repos/go-gitea/gitea/releases/latest"

    def __init__(self, custom_path: str = "", parent=None):
        super().__init__(parent)
        self.custom_path = custom_path.strip()

    def run(self):
        binary_path, binary_name = self._locate_binary()

        if not binary_path:
            self.error.emit("forgejo / gitea not found in PATH or common locations")
            return

        installed = self._get_installed_version(binary_path)
        source    = "gitea" if binary_name == "gitea" else "forgejo"
        latest    = self._fetch_latest(source)
        up_to_date = (installed != "unknown" and installed == latest)

        self.result.emit({
            "binary":     binary_name,
            "path":       binary_path,
            "installed":  installed,
            "latest":     latest,
            "source":     source,
            "up_to_date": up_to_date,
        })

    # ── private ───────────────────────────────────────────────────────

    def _locate_binary(self) -> tuple[str, str]:
        """Return (path, name) for the best forgejo/gitea binary found."""
        # 0. Manual override
        if self.custom_path:
            p = self.custom_path
            if os.path.isfile(p) and os.access(p, os.X_OK):
                base = os.path.basename(p).lower().replace(".exe", "")
                name = "gitea" if "gitea" in base else "forgejo"
                return p, name

        # 1. PATH
        for name in ("forgejo", "gitea"):
            p = shutil.which(name)
            if p:
                return p, name

        # 2. Common install locations
        common = [
            "/usr/local/bin/forgejo", "/usr/local/bin/gitea",
            os.path.expanduser("~/.local/bin/forgejo"),
            os.path.expanduser("~/.local/bin/gitea"),
        ]
        for candidate in common:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                name = "gitea" if "gitea" in candidate else "forgejo"
                return candidate, name

        return "", ""

    def _get_installed_version(self, binary_path: str) -> str:
        try:
            out = subprocess.run(
                [binary_path, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            m = self.SEMVER_RE.search(out.stdout + out.stderr)
            return m.group() if m else "unknown"
        except Exception:
            return "unknown"

    def _fetch_latest(self, source: str) -> str:
        try:
            url = self.GITEA_API if source == "gitea" else self.FORGEJO_API
            req = urllib.request.Request(url, headers={
                "User-Agent": "forgejo-installer/1.0",
                "Accept":     "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                tag  = data.get("tag_name", "")
                m    = self.SEMVER_RE.search(tag)
                return m.group() if m else "unknown"
        except Exception as e:
            return f"fetch failed ({e})"
