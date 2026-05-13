# forgejo-forge

> Part of the [Forge Suite](https://github.com/dev-boffin-io) by [@dev-boffin-io](https://github.com/dev-boffin-io)

A self-contained Git forge management suite — supports **Linux** (systemd & proot/Termux) and **Windows** (amd64 & arm64).

---

## Platform → Binary Mapping

| Platform | Binary installed | Source |
|---|---|---|
| Linux (systemd / proot / Termux) | **Forgejo** | codeberg.org/forgejo/forgejo |
| Windows 10/11 (amd64, arm64) | **Gitea** | dl.gitea.com / github.com/go-gitea/gitea |

> **Why Gitea on Windows?**
> Forgejo dropped Windows support in 2024. Gitea is Forgejo's upstream project, shares the same config format (`app.ini`), CLI flags, and admin commands — so `forgejo-forge` works identically on both.

---

## Binaries

| Binary | Description |
|---|---|
| `forgejo-forge` | CLI — setup, start, stop, restart, status, logs, email-setup, uninstall |
| `forgejo-main` | Installer — downloads Forgejo (Linux) or Gitea (Windows) |
| `forgejo-forge-gui` | PyQt6 GUI frontend for `forgejo-forge` |

---

## Data Paths

| Mode | Config | Data |
|---|---|---|
| systemd (Linux) | `/etc/forgejo/app.ini` | `/var/lib/forgejo/` |
| proot (Termux/ARM) | `~/forge-storage/forgejo/custom/conf/app.ini` | `~/forge-storage/forgejo/` |
| **Windows** | `%APPDATA%\forgejo-forge\custom\conf\app.ini` | `%APPDATA%\forgejo-forge\` |

---

## Quick Start — Windows

```powershell
# 1. Install Gitea binary
#    Downloads from dl.gitea.com → %LOCALAPPDATA%\Programs\gitea\gitea.exe
forgejo-main install

# 2. Add the printed directory to PATH, then restart your terminal

# 3. Verify
gitea --version

# 4. Setup
forgejo-forge setup --username admin --password yourpassword

# 5. Open browser → http://localhost:3000

# 6. Stop
forgejo-forge stop

# 7. Status
forgejo-forge status

# 8. Email (optional)
forgejo-forge email-setup `
  --from   git@yourdomain.com `
  --user   yourname@gmail.com `
  --passwd "xxxx xxxx xxxx xxxx"
```

> **Auto-start on login:** Task Scheduler → New Task → Trigger: At log on → Action: `forgejo-forge start`

---

## Quick Start — Linux

```bash
# 1. Install Forgejo binary
forgejo-main install

# 2. Setup (proot / Termux)
forgejo-forge setup --username admin --password yourpassword

# 3. Production (systemd, requires sudo)
sudo forgejo-forge setup --username admin --password yourpassword

# 4. Email
forgejo-forge email-setup \
  --from   git@yourdomain.com \
  --user   yourname@gmail.com \
  --passwd "xxxx xxxx xxxx xxxx"

# 5. Open GUI
forgejo-forge-gui
```

---

## forgejo-main — Binary Installer

Auto-detects OS and downloads the correct binary.

| OS | Binary | Download source |
|---|---|---|
| Linux amd64 | `forgejo` | codeberg.org |
| Linux arm64 | `forgejo` | codeberg.org |
| Linux arm | `forgejo` | codeberg.org |
| **Windows amd64** | `gitea.exe` | dl.gitea.com |
| **Windows arm64** | `gitea.exe` | dl.gitea.com |

**Install locations:**

| OS | Path |
|---|---|
| Linux | `/usr/local/bin/forgejo` |
| Windows | `%LOCALAPPDATA%\Programs\gitea\gitea.exe` |

```
forgejo-main install      # Download and install latest binary
forgejo-main update       # Check and upgrade to latest version
forgejo-main upgrade      # Same as update
forgejo-main uninstall    # Remove the binary
```

---

## forgejo-forge CLI

```
forgejo-forge setup       [--username] [--password] [--email] [--port] [--domain]
forgejo-forge start
forgejo-forge stop
forgejo-forge restart
forgejo-forge status
forgejo-forge logs        [-f] [-n <lines>]
forgejo-forge email-setup [--from] [--user] [--passwd] [--smtp-addr] [--smtp-port] [--protocol]
forgejo-forge uninstall
```

Auto-detects mode on every run:
- **systemd** — Linux with systemd; uses `/etc/forgejo/` and `/var/lib/forgejo/`
- **proot** — Linux without systemd (Termux/ARM); uses `~/forge-storage/forgejo/`
- **windows** — Windows; uses `%APPDATA%\forgejo-forge\`; process tracked via PID file

### setup flags

| Flag | Default | Description |
|---|---|---|
| `--username` | `admin` | Admin username |
| `--password` | *(required)* | Admin password |
| `--email` | `<username>@example.com` | Admin email |
| `--port` | `3000` | HTTP port (auto-increments if busy) |
| `--domain` | — | Custom domain for `ROOT_URL` |

### email-setup flags

| Flag | Default | Description |
|---|---|---|
| `--from` | *(required)* | Sender address |
| `--user` | *(required)* | SMTP login |
| `--passwd` | *(required)* | SMTP password or App Password |
| `--smtp-addr` | `smtp.gmail.com` | SMTP server |
| `--smtp-port` | `465` | SMTP port |
| `--protocol` | `smtps` | `smtps` or `smtp` (STARTTLS) |

---

## Windows-specific Notes

### Process management
Forgejo-forge tracks Gitea via `%APPDATA%\forgejo-forge\forgejo.pid`.
`stop`/`restart` use this PID; if missing, falls back to `taskkill /IM gitea.exe`.

### Logs
Pure-Go log reader (no `tail` needed). Follow mode polls every 500ms.

### Firewall
Windows Firewall may prompt to allow Gitea network access on first start — allow it.

### Auto-start (Task Scheduler)
```powershell
# Run as Administrator once:
$action  = New-ScheduledTaskAction -Execute "forgejo-forge.exe" -Argument "start"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "ForgejoForge" -Action $action -Trigger $trigger -RunLevel Highest
```

---

## Build

### Linux (native)
```bash
sudo apt install golang python3-venv
make all
make install && make install-installer
```

### Cross-compile Windows from Linux
```bash
make build-windows          # bin/forgejo-forge-windows-amd64.exe
make build-windows-arm64    # bin/forgejo-forge-windows-arm64.exe
make installer-windows      # bin/forgejo-main-windows-amd64.exe
make installer-windows-arm64 # bin/forgejo-main-windows-arm64.exe
```

### Windows native (requires Go)
```powershell
go build -o bin\forgejo-forge.exe .
cd forgejo-installer && go build -o ..\bin\forgejo-main.exe .
```

---

## Project Structure

```
forgejo-forge/
├── main.go
├── cmd/                        # CLI subcommands (setup/start/stop/restart/status/logs/email/uninstall)
├── internal/
│   ├── admin/create.go         # admin user create (Forgejo & Gitea compatible)
│   ├── config/                 # app.ini writer, reader, mailer patcher
│   ├── detect/env.go           # mode detection; ForgejoBin() → gitea.exe on Windows
│   ├── netutil/                # port detection, LAN IP, cloudflared
│   ├── runner/                 # process management (GITEA_WORK_DIR on Windows)
│   └── svc/                    # paths, status, uninstall
├── forgejo-installer/          # forgejo-main sub-project
│   └── internal/
│       ├── arch/arch.go        # Linux→Forgejo, Windows→Gitea routing
│       ├── download/           # dual-source downloader (Codeberg / dl.gitea.com)
│       ├── install/            # install/uninstall binary
│       └── version/            # version fetch (Codeberg API / GitHub API)
├── gui/                        # PyQt6 GUI
└── Makefile
```

---

## License

MIT License — see [LICENSE](LICENSE)
