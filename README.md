# forgejo-forge

> Part of the [Forge Suite](https://github.com/dev-boffin-io) by [@dev-boffin-io](https://github.com/dev-boffin-io)

A self-contained Forgejo management suite for Linux — supports both production
(systemd) and proot/Termux (ARM64) environments.

---

## Binaries

| Binary | Description |
|--------|-------------|
| `forgejo-forge` | CLI — setup, start, stop, restart, status, logs, email-setup, uninstall |
| `forgejo-main` | Installer — install, update, upgrade, uninstall Forgejo binary |
| `forgejo-forge-gui` | PyQt6 GUI frontend for `forgejo-forge` |

---

## Requirements

- Linux (Debian/Ubuntu, or proot/Termux ARM64)
- `forgejo` binary in `PATH` (install with `forgejo-main`)
- Python 3.10+ and `python3-venv` (GUI build only)

---

## Quick Start

```bash
# 1. Install Forgejo binary
forgejo-main install

# 2. Setup Forgejo (proot / Termux)
forgejo-forge setup --username admin --password yourpassword

# 3. Or with custom port and domain
forgejo-forge setup --username admin --password yourpassword --port 3000 --domain git.local

# 4. Check status
forgejo-forge status

# 5. Configure email (optional)
forgejo-forge email-setup \
  --from   forgejo@yourdomain.com \
  --user   yourname@gmail.com \
  --passwd "xxxx xxxx xxxx xxxx"

# 6. Open GUI
forgejo-forge-gui
```

For systemd (production server):
```bash
sudo forgejo-forge setup --username admin --password yourpassword
```

---

## forgejo-main — Forgejo Binary Installer

Downloads and manages the official Forgejo binary from GitHub releases.
Auto-detects architecture (amd64, arm64, riscv64).

```bash
forgejo-main install      # Download and install latest Forgejo
forgejo-main update       # Check for updates
forgejo-main upgrade      # Upgrade to latest version
forgejo-main uninstall    # Remove Forgejo binary
```

---

## forgejo-forge CLI

```bash
forgejo-forge setup       [--username] [--password] [--email] [--port] [--domain]
forgejo-forge start
forgejo-forge stop
forgejo-forge restart
forgejo-forge status
forgejo-forge logs        [-f] [-n <lines>]
forgejo-forge email-setup [--from] [--user] [--passwd] [--smtp-addr] [--smtp-port] [--protocol]
forgejo-forge uninstall
```

Auto-detects environment on every run:
- **systemd mode** — requires `sudo`, uses `/etc/forgejo/` and `/var/lib/forgejo/`
- **proot mode** — runs as current user, uses `~/forge-storage/forgejo/`

### Setup flags

| Flag | Default | Description |
|------|---------|-------------|
| `--username` | `admin` | Admin username |
| `--password` | *(required)* | Admin password |
| `--email` | `<username>@example.com` | Admin email |
| `--port` | `3000` | HTTP port (auto-increments if busy) |
| `--domain` | — | Custom domain for `ROOT_URL` |

### email-setup flags

Patches (or appends) the `[mailer]` section in the active `app.ini`.
Run `forgejo-forge restart` after applying to activate the changes.

| Flag | Default | Description |
|------|---------|-------------|
| `--from` | *(required)* | Sender address shown in outgoing mail |
| `--user` | *(required)* | SMTP login username (usually your email) |
| `--passwd` | *(required)* | SMTP password or App Password |
| `--smtp-addr` | `smtp.gmail.com` | SMTP server hostname |
| `--smtp-port` | `465` | SMTP port (465 for smtps, 587 for smtp/STARTTLS) |
| `--protocol` | `smtps` | `smtps` (SSL/TLS) or `smtp` (STARTTLS) |

**Examples:**

```bash
# Gmail with App Password (smtps / port 465)
forgejo-forge email-setup \
  --from   forgejo@yourdomain.com \
  --user   yourname@gmail.com \
  --passwd "xxxx xxxx xxxx xxxx" \
  --smtp-addr smtp.gmail.com \
  --smtp-port 465 --protocol smtps

# Brevo / Mailgun STARTTLS (port 587)
forgejo-forge email-setup \
  --from   forgejo@yourdomain.com \
  --user   apikey \
  --passwd "your-api-key" \
  --smtp-addr smtp-relay.brevo.com \
  --smtp-port 587 --protocol smtp
```

> **Gmail tip:** Enable 2FA on your Google account, then generate an App Password at
> [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
> Free alternatives: [Brevo](https://www.brevo.com), Mailgun, Cloudflare Email Routing.

After setting up email, test it from the Forgejo Admin Panel:
**Site Administration → Configuration → SMTP Mailer Configuration → Send Test Mail**

### Data paths

| Mode | Config | Data |
|------|--------|------|
| systemd | `/etc/forgejo/app.ini` | `/var/lib/forgejo/` |
| proot | `~/forge-storage/forgejo/custom/conf/app.ini` | `~/forge-storage/forgejo/` |

### Package registries

All Forgejo package registries are enabled by default:

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
make build              # bin/forgejo-forge  (native)
make build-arm64        # bin/forgejo-forge-arm64
make installer          # bin/forgejo-main   (native)
make installer-arm64    # bin/forgejo-main-arm64
make gui-build          # bin/forgejo-forge-gui (PyInstaller)

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
forgejo-forge/
├── main.go                     # forgejo-forge CLI entry point
├── cmd/                        # CLI subcommands
│   ├── setup.go
│   ├── start.go  stop.go  restart.go
│   ├── status.go  logs.go  uninstall.go
│   ├── email.go                # email-setup command
│   └── root.go
├── internal/
│   ├── admin/      # forgejo admin user create wrapper
│   ├── config/     # app.ini writer, reader, mailer patcher
│   ├── detect/     # systemd vs proot detection
│   ├── netutil/    # port detection, LAN IP, cloudflared URL
│   ├── runner/     # background process management
│   └── svc/        # status, paths, uninstall logic
├── forgejo-installer/            # forgejo-main sub-project
│   ├── main.go
│   ├── cmd/
│   └── internal/
│       ├── arch/       # architecture detection
│       ├── download/   # GitHub release downloader
│       ├── install/    # install/uninstall logic
│       └── version/    # version fetching
├── gui/
│   ├── forgejo-forge.py          # PyQt6 GUI (tabs: Setup · Control · Email · Logs)
│   ├── forgejo-forge.png         # App icon
│   └── requirements.txt
└── Makefile
```

---

## License

MIT License — see [LICENSE](LICENSE)
