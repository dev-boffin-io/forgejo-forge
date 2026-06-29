"""
Background worker threads for all long-running Git operations.
Cross-platform: Windows, macOS, Linux, Termux, proot-distro.
Python 3.9+ compatible.
"""
from __future__ import annotations

import os
import sys
import platform
import subprocess
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

from forge_git_manager.git_config import get_git_path, _is_termux, _is_root


# ── Cross-platform subprocess helper ─────────────────────────────────────────

def _run_git(*args, cwd=None, timeout=120, env=None):
    """
    Run a git command using the user-configured binary path.
    Returns (returncode, stdout, stderr).
    """
    cmd = [get_git_path()] + list(args)

    kwargs = dict(
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    run_env = os.environ.copy()
    run_env["GIT_TERMINAL_PROMPT"] = "0"
    run_env["LANG"] = "en_US.UTF-8"
    run_env["LC_ALL"] = "en_US.UTF-8"
    if env:
        run_env.update(env)
    kwargs["env"] = run_env

    result = subprocess.run(cmd, **kwargs)
    return result.returncode, result.stdout, result.stderr


# ── Extractor Worker ──────────────────────────────────────────────────────────

class ExtractorWorker(QThread):
    """git archive → zip for bare repos."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, selected_repos: list[str], source_dir: str, output_dir: str):
        super().__init__()
        self.selected_repos = selected_repos
        self.source_dir = source_dir
        self.output_dir = output_dir

    def run(self):
        total = len(self.selected_repos)
        success_count = 0
        fail_count = 0

        for idx, repo in enumerate(self.selected_repos, start=1):
            repo_path = os.path.join(self.source_dir, repo)
            project_name = repo.removesuffix(".git")
            zip_filename = f"{project_name}.zip"
            zip_path = os.path.join(self.output_dir, zip_filename)

            self.progress_signal.emit(f"[{idx}/{total}]  ⏳  Archiving  {project_name} ...")

            try:
                rc, out, err = _run_git(
                    "-C", repo_path, "archive", "--format=zip", "HEAD", "-o", zip_path,
                    timeout=120,
                )
                if rc == 0:
                    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                    self.progress_signal.emit(
                        f"[{idx}/{total}]  ✅  {zip_filename}  ({size_mb:.2f} MB)"
                    )
                    success_count += 1
                else:
                    self.progress_signal.emit(
                        f"[{idx}/{total}]  ❌  {project_name}  →  {(err or out).strip() or 'Unknown error'}"
                    )
                    fail_count += 1
            except subprocess.TimeoutExpired:
                self.progress_signal.emit(
                    f"[{idx}/{total}]  ⏱️  {project_name}  →  Timed out after 120 s"
                )
                fail_count += 1
            except FileNotFoundError:
                self.progress_signal.emit(
                    "❌  git not found — please install Git and make sure it is on your PATH."
                )
                fail_count += total - idx + 1
                break
            except Exception as e:
                self.progress_signal.emit(f"[{idx}/{total}]  ⚠️  {project_name}  →  {e}")
                fail_count += 1

        self.progress_signal.emit(
            f"\n{'─' * 50}\n"
            f"🎉  Done!  {success_count} succeeded"
            + (f",  {fail_count} failed." if fail_count else ".")
        )
        self.finished_signal.emit()


# ── Git Init Worker ───────────────────────────────────────────────────────────

class GitInitWorker(QThread):
    """git init + first commit for project folders."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, projects_dir: str, single_folder: bool = False):
        super().__init__()
        self.projects_dir = projects_dir
        self.single_folder = single_folder

    def run(self):
        base = self.projects_dir
        if not os.path.isdir(base):
            self.progress_signal.emit(f"❌  Directory not found: {base}")
            self.finished_signal.emit()
            return

        if self.single_folder:
            # Run directly on the selected folder itself
            folders = [("", base)]   # (display_name, full_path)
        else:
            subdirs = sorted(
                d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))
            )
            if not subdirs:
                self.progress_signal.emit("⚠️  No subdirectories found.")
                self.finished_signal.emit()
                return
            folders = [(d, os.path.join(base, d)) for d in subdirs]

        for display, path in folders:
            label = display or os.path.basename(path)
            self.progress_signal.emit(f"\n🚀  Initializing Git in: {label}")

            if os.path.isdir(os.path.join(path, ".git")):
                self.progress_signal.emit("⚠️  Already a Git repository — skipping.")
                continue

            try:
                self._git("init", cwd=path)
                self._git("add", ".", cwd=path)

                rc, _, _ = _run_git("diff", "--cached", "--quiet", cwd=path, timeout=30)
                if rc != 0:
                    self._git("commit", "-m", "Initial commit: Added Release v-1.0.0", cwd=path)
                else:
                    self.progress_signal.emit("📂  Nothing to commit.")

                self._git("branch", "-M", "main", cwd=path)
                self.progress_signal.emit(f"✅  Completed: {label}")
                self.progress_signal.emit("─" * 40)

            except FileNotFoundError:
                self.progress_signal.emit(
                    "❌  git not found — please install Git and make sure it is on your PATH."
                )
                break
            except Exception as e:
                self.progress_signal.emit(f"❌  Error in {label}: {e}")

        self.progress_signal.emit("\n🎉  All done!")
        self.finished_signal.emit()

    def _git(self, *args, cwd):
        rc, out, err = _run_git(*args, cwd=cwd, timeout=60)
        if out.strip():
            self.progress_signal.emit(out.strip())
        if err.strip():
            self.progress_signal.emit(err.strip())


# ── Git Remote Worker ─────────────────────────────────────────────────────────

class GitRemoteWorker(QThread):
    """Add 'local' remote to each project."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, projects_dir: str, username: str, token: str, host: str,
                 single_folder: bool = False):
        super().__init__()
        self.projects_dir = projects_dir
        self.username = username
        self.token = token
        self.host = host
        self.single_folder = single_folder

    def run(self):
        base = self.projects_dir
        if not os.path.isdir(base):
            self.progress_signal.emit(f"❌  Directory not found: {base}")
            self.finished_signal.emit()
            return

        self.progress_signal.emit("=" * 40)
        self.progress_signal.emit("🚀  Configuring Git remotes...")
        self.progress_signal.emit("=" * 40)

        if self.single_folder:
            folders = [(os.path.basename(base), base)]
        else:
            subdirs = sorted(
                d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))
            )
            folders = [(d, os.path.join(base, d)) for d in subdirs]

        for folder_name, path in folders:
            self.progress_signal.emit(f"\n📁  Project: {folder_name}")

            if not os.path.isdir(os.path.join(path, ".git")):
                self.progress_signal.emit("⚠️  Not a Git repository — skipping.")
                continue

            try:
                rc, url_out, _ = _run_git("remote", "get-url", "local", cwd=path, timeout=15)
                if rc == 0:
                    self.progress_signal.emit("⚠️  Remote 'local' already exists.")
                    self.progress_signal.emit(f"🔗  {url_out.strip()}")
                else:
                    remote_url = (
                        f"http://{self.username}:{self.token}"
                        f"@{self.host}/{self.username}/{folder_name}.git"
                    )
                    rc2, _, err2 = _run_git(
                        "remote", "add", "local", remote_url, cwd=path, timeout=15
                    )
                    if rc2 == 0:
                        masked = remote_url.replace(self.token, "****")
                        self.progress_signal.emit("✅  Remote 'local' added.")
                        self.progress_signal.emit(f"🔗  {masked}")
                    else:
                        self.progress_signal.emit(f"❌  Failed: {err2.strip()}")

            except FileNotFoundError:
                self.progress_signal.emit(
                    "❌  git not found — please install Git and make sure it is on your PATH."
                )
                break
            except Exception as e:
                self.progress_signal.emit(f"❌  Error: {e}")

            self.progress_signal.emit("─" * 40)

        self.progress_signal.emit("\n🎉  Done! All repositories have been processed.")
        self.finished_signal.emit()


# ── Git Push Worker ───────────────────────────────────────────────────────────

class GitPushWorker(QThread):
    """Push each project to 'local' remote."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, projects_dir: str):
        super().__init__()
        self.projects_dir = projects_dir

    def run(self):
        base = self.projects_dir
        if not os.path.isdir(base):
            self.progress_signal.emit(f"❌  Directory not found: {base}")
            self.finished_signal.emit()
            return

        self.progress_signal.emit("=" * 40)
        self.progress_signal.emit("🚀  Pushing repositories to 'local' remote...")
        self.progress_signal.emit("=" * 40)

        folders = sorted(
            d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))
        )

        for folder in folders:
            path = os.path.join(base, folder)
            self.progress_signal.emit(f"\n⬆️  Pushing: {folder}")

            if not os.path.isdir(os.path.join(path, ".git")):
                self.progress_signal.emit("⚠️  Not a Git repository — skipping.")
                continue

            rc, _, _ = _run_git("remote", "get-url", "local", cwd=path, timeout=15)
            if rc != 0:
                self.progress_signal.emit("⚠️  Remote 'local' not found — skipping.")
                continue

            try:
                rc2, out2, err2 = _run_git("push", "-u", "local", "main", cwd=path, timeout=120)
                if rc2 == 0:
                    self.progress_signal.emit(f"✅  Pushed: {folder}")
                    if err2.strip():
                        self.progress_signal.emit(err2.strip())
                else:
                    msg = (err2 or out2).strip() or "Unknown error"
                    self.progress_signal.emit(f"❌  Failed: {folder}\n    {msg}")
            except subprocess.TimeoutExpired:
                self.progress_signal.emit(f"⏱️  Timed out: {folder}")
            except FileNotFoundError:
                self.progress_signal.emit(
                    "❌  git not found — please install Git and make sure it is on your PATH."
                )
                break
            except Exception as e:
                self.progress_signal.emit(f"❌  Error: {e}")

            self.progress_signal.emit("─" * 40)

        self.progress_signal.emit("\n🎉  All repositories have been processed.")
        self.finished_signal.emit()


# ── Clone Worker ──────────────────────────────────────────────────────────────

class CloneWorker(QThread):
    """Clone repos from Forgejo bare storage to a destination folder."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, repos: list[str], source_dir: str, desktop_dir: str,
                 username: str, token: str, host: str):
        super().__init__()
        self.repos = repos
        self.source_dir = source_dir
        self.desktop_dir = desktop_dir
        self.username = username
        self.token = token
        self.host = host

    def run(self):
        total = len(self.repos)
        success = 0
        failed = 0

        for idx, repo_name in enumerate(self.repos, start=1):
            project_name = repo_name.removesuffix(".git")
            clone_target = os.path.join(self.desktop_dir, f"{project_name}-source-code")

            self.progress_signal.emit(f"\n[{idx}/{total}]  🔄  Cloning: {project_name}")

            if os.path.isdir(clone_target):
                self.progress_signal.emit(f"⚠️  Already cloned at: {clone_target}")
                success += 1
                continue

            clone_url = (
                f"http://{self.username}:{self.token}"
                f"@{self.host}/{self.username}/{project_name}.git"
            )
            masked_url = clone_url.replace(self.token, "****")
            self.progress_signal.emit(f"🔗  {masked_url}")

            try:
                rc, out, err = _run_git("clone", clone_url, clone_target, timeout=180)
                if rc == 0:
                    self.progress_signal.emit(f"✅  Cloned → {clone_target}")
                    success += 1
                else:
                    msg = (err or out).strip().replace(self.token, "****") or "Unknown error"
                    self.progress_signal.emit(f"❌  Failed: {msg}")
                    failed += 1
            except subprocess.TimeoutExpired:
                self.progress_signal.emit("⏱️  Timed out after 180 s")
                failed += 1
            except FileNotFoundError:
                self.progress_signal.emit(
                    "❌  git not found — please install Git and make sure it is on your PATH."
                )
                failed += total - idx + 1
                break
            except Exception as e:
                self.progress_signal.emit(f"❌  Error: {e}")
                failed += 1

            self.progress_signal.emit("─" * 40)

        self.progress_signal.emit(
            f"\n{'─' * 50}\n"
            f"🎉  Done!  {success} cloned"
            + (f",  {failed} failed." if failed else ".")
        )
        self.finished_signal.emit()


# ── Delete Clone Worker ───────────────────────────────────────────────────────

class DeleteCloneWorker(QThread):
    """Remove *-source-code folders."""

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, folders: list[str], desktop_dir: str):
        super().__init__()
        self.folders = folders
        self.desktop_dir = desktop_dir

    def run(self):
        total = len(self.folders)
        success = 0

        for idx, folder_name in enumerate(self.folders, start=1):
            path = os.path.join(self.desktop_dir, folder_name)
            self.progress_signal.emit(f"\n[{idx}/{total}]  🗑️  Removing: {folder_name}")

            try:
                if platform.system() == "Windows":
                    # On Windows, shutil.rmtree can fail on read-only files
                    # (common in git repos). Use onerror to force-remove them.
                    def _force_remove(func, fpath, _):
                        os.chmod(fpath, 0o777)
                        func(fpath)
                    shutil.rmtree(path, onerror=_force_remove)
                else:
                    shutil.rmtree(path)
                self.progress_signal.emit(f"✅  Removed: {path}")
                success += 1
            except Exception as e:
                self.progress_signal.emit(f"❌  Failed to remove {folder_name}: {e}")

        self.progress_signal.emit(
            f"\n{'─' * 50}\n🎉  Done!  {success}/{total} removed."
        )
        self.finished_signal.emit()



# ── Git Binary Install / Upgrade Worker ───────────────────────────────────────


class GitBinaryWorker(QThread):
    """
    Run an install/upgrade command for git.
    Mirrors ollama-forge ManageWorker sudo logic:
    - Termux → run directly, no sudo
    - proot-distro / root → run directly, no sudo
    - sudo_password provided → pipe to 'sudo -kS'
    - needs_admin but no password → tell user to enter password
    """

    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, cmd: list[str], needs_sudo: bool = False,
                 sudo_password: str | None = None):
        super().__init__()
        self.cmd = cmd
        self.needs_sudo = needs_sudo
        self.sudo_password = sudo_password
        self._cancelled = False

    def run(self):
        if not self.cmd:
            self.progress_signal.emit("❌  No install command available for this platform.")
            self.finished_signal.emit()
            return

        system = platform.system()
        termux  = _is_termux()
        as_root = _is_root()

        cmd = list(self.cmd)
        use_sudo = False

        if self.needs_sudo and system != "Windows" and not termux and not as_root:
            if self.sudo_password:
                use_sudo = True
            else:
                self.progress_signal.emit(
                    "⚠️  This command requires root/sudo access.\n"
                    "    Please enter your sudo password in the field above and try again.\n\n"
                    f"    Or run manually in a terminal:\n"
                    f"    sudo {' '.join(self.cmd)}"
                )
                self.finished_signal.emit()
                return

        label = ("sudo " if use_sudo else "") + " ".join(cmd)
        self.progress_signal.emit(f"▶  Running: {label}\n{'─'*50}")

        try:
            popen_kwargs: dict = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if system == "Windows":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore

            if use_sudo:
                # sudo -kS: -k resets timestamp, -S reads password from stdin
                popen_kwargs["stdin"] = subprocess.PIPE
                process = subprocess.Popen(["sudo", "-kS"] + cmd, **popen_kwargs)
                process.stdin.write(self.sudo_password + "\n")  # type: ignore
                process.stdin.close()  # type: ignore
            else:
                process = subprocess.Popen(cmd, **popen_kwargs)

            for line in process.stdout:  # type: ignore
                if self._cancelled:
                    process.terminate()
                    self.progress_signal.emit("⛔  Cancelled.")
                    self.finished_signal.emit()
                    return
                stripped = line.rstrip()
                # Hide sudo password echo
                if stripped and "password" not in stripped.lower():
                    self.progress_signal.emit(stripped)

            process.wait(timeout=300)

            if process.returncode == 0:
                self.progress_signal.emit("\n✅  Completed successfully.")
            else:
                self.progress_signal.emit(f"\n⚠️  Exited with code {process.returncode}.")

        except FileNotFoundError as e:
            self.progress_signal.emit(
                f"❌  Command not found: {cmd[0]}\n"
                f"    Make sure the package manager is installed.\n"
                f"    Details: {e}"
            )
        except subprocess.TimeoutExpired:
            self.progress_signal.emit("⏱️  Timed out after 300 s.")
        except Exception as e:
            self.progress_signal.emit(f"❌  Unexpected error: {e}")

        self.finished_signal.emit()

    def cancel(self):
        self._cancelled = True
