# gitea-forge

> Part of the [Forge Suite](https://github.com/dev-boffin-io) by [@dev-boffin-io](https://github.com/dev-boffin-io)

A self-contained Gitea management suite for Linux — supports both production
(systemd) and proot/Termux (ARM64) environments.

---

## Binaries

| Binary | Description |
|--------|-------------|
| `gitea-forge` | CLI — setup, start, stop, restart, status, logs, uninstall |
| `gitea-main` | Installer — install, update, upgrade, uninstall Gitea binary |
| `gitea-forge-gui` | PyQt6 GUI frontend for `gitea-forge` |

---

## Requirements

- Linux (Debian/Ubuntu, or proot/Termux ARM64)
- `gitea` binary in `PATH` (install with `gitea-main`)
- Python 3.10+ and `python3-venv` (GUI build only)

---

## Quick Start

```bash
# 1. Install Gitea binary
gitea-main install

# 2. Setup Gitea (proot / Termux)
gitea-forge setup --username admin --password yourpassword

# 3. Or with custom port and domain
gitea-forge setup --username admin --password yourpassword --port 3000 --domain git.local

# 4. Check status
gitea-forge status

# 5. Open GUI
gitea-forge-gui
```

For systemd (production server):
```bash
sudo gitea-forge setup --username admin --password yourpassword
```

---

## gitea-main — Gitea Binary Installer

Downloads and manages the official Gitea binary from GitHub releases.
Auto-detects architecture (amd64, arm64, riscv64).

```bash
gitea-main install      # Download and install latest Gitea
gitea-main update       # Check for updates
gitea-main upgrade      # Upgrade to latest version
gitea-main uninstall    # Remove Gitea binary
```

---

## gitea-forge CLI

```bash
gitea-forge setup      [--username] [--password] [--email] [--port] [--domain]
gitea-forge start
gitea-forge stop
gitea-forge restart
gitea-forge status
gitea-forge logs       [-f] [-n <lines>]
gitea-forge uninstall
```

Auto-detects environment on every run:
- **systemd mode** — requires `sudo`, uses `/etc/gitea/` and `/var/lib/gitea/`
- **proot mode** — runs as current user, uses `~/forge-storage/gitea/`

### Setup flags

| Flag | Default | Description |
|------|---------|-------------|
| `--username` | `admin` | Admin username |
| `--password` | *(required)* | Admin password |
| `--email` | `<username>@example.com` | Admin email |
| `--port` | `3000` | HTTP port (auto-increments if busy) |
| `--domain` | — | Custom domain for `ROOT_URL` |

### Data paths

| Mode | Config | Data |
|------|--------|------|
| systemd | `/etc/gitea/app.ini` | `/var/lib/gitea/` |
| proot | `~/forge-storage/gitea/custom/conf/app.ini` | `~/forge-storage/gitea/` |

### Package registries

All Gitea package registries are enabled by default:

| Type | Endpoint |
|------|----------|
| Go modules | `http://localhost:3000/api/packages/{user}/go` |
| Debian/APT | `http://localhost:3000/api/packages/{user}/debian/...` |
| Generic | `http://localhost:3000/api/packages/{user}/generic/...` |
| Docker/OCI | `localhost:3000/{user}/{image}` |

---

## Build

```bash
# Dependencies
sudo apt install golang python3-venv

# Build everything
make all

# Individual targets
make build              # bin/gitea-forge  (native)
make build-arm64        # bin/gitea-forge-arm64
make installer          # bin/gitea-main   (native)
make installer-arm64    # bin/gitea-main-arm64
make gui-build          # bin/gitea-forge-gui (PyInstaller)

# Install to ~/.local/bin/
make install
make install-installer
make install-gui        # + .desktop entry

# Uninstall
make uninstall

# Clean
make clean

# Help
make help
```

---

## Project Structure

```
gitea-forge/
├── main.go                     # gitea-forge CLI entry point
├── cmd/                        # CLI subcommands
│   ├── setup.go
│   ├── start.go  stop.go  restart.go
│   ├── status.go  logs.go  uninstall.go
│   └── root.go
├── internal/
│   ├── admin/      # gitea admin user create wrapper
│   ├── config/     # app.ini writer + reader
│   ├── detect/     # systemd vs proot detection
│   ├── netutil/    # port detection, LAN IP, cloudflared URL
│   ├── runner/     # background process management
│   └── svc/        # status, paths, uninstall logic
├── gitea-installer/            # gitea-main sub-project
│   ├── main.go
│   ├── cmd/
│   └── internal/
│       ├── arch/       # architecture detection
│       ├── download/   # GitHub release downloader
│       ├── install/    # install/uninstall logic
│       └── version/    # version fetching
├── gui/
│   ├── gitea-forge.py          # PyQt6 GUI
│   ├── gitea-forge.png         # App icon
│   └── requirements.txt
└── Makefile
```

---

## License

MIT License — see [LICENSE](LICENSE)
