# forgejo-forge

> Part of the [Forge Suite](https://github.com/dev-boffin-io) by [@dev-boffin-io](https://github.com/dev-boffin-io)

A self-contained Git forge management suite — supports **Linux** (systemd & proot/Termux), **Windows** (amd64 & arm64), and **macOS** (amd64 & arm64).

---

## Platform → Binary Mapping

| Platform | Binary installed | Source |
|---|---|---|
| Linux (systemd / proot / Termux) | **Forgejo** | codeberg.org/forgejo/forgejo |
| Windows 10/11 (amd64, arm64) | **Gitea** | dl.gitea.com / github.com/go-gitea/gitea |
| macOS (amd64, arm64) | **Forgejo** | codeberg.org/forgejo/forgejo |

> **Why Gitea on Windows?**
> Forgejo dropped Windows support in 2024. Gitea is Forgejo's upstream project, shares the same config format (`app.ini`), CLI flags, and admin commands — so `forgejo-forge` works identically on both.

> **macOS support**
> The CLI and `forgejo-main` installer build and run on macOS (amd64/arm64) using the same generic, non-systemd code path as proot/Termux (`~/forge-storage/forgejo/`). The GUI requires a native PyInstaller build on macOS — see [Build](#build).

---

## Binaries

| Binary | Description |
|---|---|
| `forgejo-forge` | CLI — setup, start, stop, restart, status, logs, email-setup, config, uninstall |
| `forgejo-main` | Installer — downloads Forgejo (Linux) or Gitea (Windows) |
| `forgejo-forge-gui` | PyQt6 GUI frontend for `forgejo-forge` |

---

## Data Paths

| Mode | Config | Data |
|---|---|---|
| systemd (Linux) | `/etc/forgejo/app.ini` | `/var/lib/forgejo/` |
| proot (Termux/ARM) | `~/forge-storage/forgejo/custom/conf/app.ini` | `~/forge-storage/forgejo/` |
| macOS | `~/forge-storage/forgejo/custom/conf/app.ini` | `~/forge-storage/forgejo/` |
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

## Quick Start — macOS

```bash
# 1. Install Forgejo binary → ~/forge-storage/forgejo/bin/forgejo
forgejo-main install

# 2. Setup
forgejo-forge setup --username admin --password yourpassword

# 3. Open browser → http://localhost:3000

# 4. Stop / status / logs
forgejo-forge stop
forgejo-forge status
forgejo-forge logs -f

# 5. Email (optional)
forgejo-forge email-setup \
  --from   git@yourdomain.com \
  --user   yourname@gmail.com \
  --passwd "xxxx xxxx xxxx xxxx"
```

> **Auto-start on login:** `launchd` — create a `LaunchAgent` plist that runs `forgejo-forge start` at login.

---

## forgejo-main — Binary Installer

Auto-detects OS and downloads the correct binary.

| OS | Binary | Download source |
|---|---|---|
| Linux amd64 | `forgejo` | codeberg.org |
| Linux arm64 | `forgejo` | codeberg.org |
| Linux arm | `forgejo` | codeberg.org |
| **macOS amd64** | `forgejo` | codeberg.org |
| **macOS arm64** | `forgejo` | codeberg.org |
| **Windows amd64** | `gitea.exe` | dl.gitea.com |
| **Windows arm64** | `gitea.exe` | dl.gitea.com |

**Install locations:**

| OS | Path |
|---|---|
| Linux | `/usr/local/bin/forgejo` |
| macOS | `~/forge-storage/forgejo/bin/forgejo` |
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
forgejo-forge setup       [--username] [--password] [--email] [--port] [--domain] [--actions]
forgejo-forge start
forgejo-forge stop
forgejo-forge restart
forgejo-forge status
forgejo-forge logs        [-f] [-n <lines>]
forgejo-forge email-setup [--from] [--user] [--passwd] [--smtp-addr] [--smtp-port] [--protocol]
forgejo-forge config      path | sections | list | get | set | remove | raw-get | raw-set | enable-actions
forgejo-forge uninstall
```

Auto-detects mode on every run:
- **systemd** — Linux with systemd; uses `/etc/forgejo/` and `/var/lib/forgejo/`
- **proot** — Linux without systemd (Termux/ARM) or **macOS**; uses `~/forge-storage/forgejo/`
- **windows** — Windows; uses `%APPDATA%\forgejo-forge\`; process tracked via PID file

### setup flags

| Flag | Default | Description |
|---|---|---|
| `--username` | `admin` | Admin username |
| `--password` | *(required)* | Admin password |
| `--email` | `<username>@example.com` | Admin email |
| `--port` | `3000` | HTTP port (auto-increments if busy) |
| `--domain` | — | Custom domain for `ROOT_URL` |
| `--actions` | `false` | Enable Forgejo Actions (CI/CD) + local artifact storage in `app.ini` |

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

## Config (app.ini)

`forgejo-forge config` reads and edits the `app.ini` written by `setup`, without needing to know which mode (systemd/proot/Windows) is active — it resolves the same path `setup` would use.

```
forgejo-forge config path                            # print resolved app.ini path
forgejo-forge config sections                         # list all [section] names
forgejo-forge config list <section>                   # list key=value pairs in a section
forgejo-forge config get <section> <key>               # print one value
forgejo-forge config set <section> <key> <value>       # set/add a key (creates section if needed)
forgejo-forge config remove <section> <key>            # remove a key (drops section if it becomes empty)
forgejo-forge config raw-get                            # print the entire app.ini
forgejo-forge config raw-set                            # replace app.ini from stdin (writes app.ini.bak first)
forgejo-forge config enable-actions                     # enable [actions] + [actions.artifacts] on an existing install
```

`set`/`remove`/`raw-set`/`enable-actions` don't restart Forgejo automatically — run `forgejo-forge restart` afterwards for changes to take effect.

`enable-actions` is the same logic as `setup --actions`, but for an install that's already configured — it writes:

```ini
[actions]
ENABLED = true

[actions.artifacts]
STORAGE_TYPE = local
PATH = <data-dir>/artifacts
```

> The GUI exposes this as **📝 Edit app.ini** (full editor with syntax highlighting + warnings for duplicate sections / malformed lines) and **Apply Now** next to the Actions checkbox (runs `config enable-actions` without re-running setup).

---

## Runner (CI / Forgejo Actions)

`forgejo-forge runner` manages a [forgejo-runner](https://code.forgejo.org/forgejo/runner) / [gitea-runner](https://gitea.com/gitea/runner) instance — the agent that picks up Forgejo Actions / CI jobs.

```
forgejo-forge runner install                                  # download + install
forgejo-forge runner register --url <URL> --token <TOKEN> \
                                --uuid <UUID> --name <NAME> \
                                --labels ubuntu-latest:host \
                                [--clean]
forgejo-forge runner start
forgejo-forge runner stop
forgejo-forge runner status
forgejo-forge runner uninstall
```

| OS | Binary | Download source |
|---|---|---|
| Linux | `forgejo-runner` | code.forgejo.org / data.forgejo.org |
| Windows / macOS | `gitea-runner` | gitea.com/gitea/runner |

### register flags

| Flag | Default | Description |
|---|---|---|
| `--url` | *(required)* | Forgejo/Gitea instance URL |
| `--token` | *(required)* | Registration token from **Settings → Actions → Runners → Create new runner** |
| `--uuid` | — | UUID shown on the same "Create new runner" page — **use this for a clean first-time registration** |
| `--name` | hostname | Runner display name |
| `--labels` | `ubuntu-latest:host` | Comma-separated labels. `:host` runs jobs directly (no Docker required) |
| `--clean` | `false` | Discard existing `config.yml` / `.runner` and start fresh |
| `--runner-bin` | auto-detect | Override path to the runner binary |

> **First-time registration:** copy both the **UUID** and **Token** from the "Create new runner" page and pass both `--uuid` and `--token`. A registration token binds to whatever UUID is first used with it — re-registering with a different (random) UUID while reusing the same token causes `unauthenticated: unregistered runner`. `register` (without `--uuid`) re-uses whatever UUID is already in `config.yml`, so it's safe to re-run.

> **Docker not available?** (e.g. Termux/proot) Use `:host` labels (the default) — jobs run directly on the host shell instead of inside a container.

Config lives at `~/.config/forgejo-runner/config.yml` (Linux/macOS) — same data-path convention as Forgejo itself.

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

### Cross-compile macOS from Linux
```bash
GOOS=darwin GOARCH=amd64 go build -o bin/forgejo-forge-darwin-amd64 .
GOOS=darwin GOARCH=arm64 go build -o bin/forgejo-forge-darwin-arm64 .
cd forgejo-installer
GOOS=darwin GOARCH=amd64 go build -o ../bin/forgejo-main-darwin-amd64 .
GOOS=darwin GOARCH=arm64 go build -o ../bin/forgejo-main-darwin-arm64 .
```

### macOS native (requires Go + Python)
```bash
brew install go python3
make all
make install && make install-installer && make install-gui
```

> **GUI on macOS:** PyInstaller does not cross-compile — the `.app`/binary for macOS **must** be built on an actual Mac (or a macOS CI runner). `make gui-build` works the same way as on Linux once run on macOS.

### CI (GitHub / Forgejo Actions)
| Workflow | Builds |
|---|---|
| `build-linux-amd64.yml` / `build-linux-arm64.yml` | CLI + installer (Linux) |
| `build-windows-amd64.yml` / `build-windows-arm64.yml` | CLI + installer (Windows) |
| `build-macos.yml` | CLI + installer (macOS, cross-compiled) |
| `build-gui-linux-amd64.yml` / `build-gui-linux-arm64.yml` | GUI (Linux) |
| `build-gui-windows-amd64.yml` | GUI (Windows) |
| `build-gui-macos.yml` | GUI (macOS) — **requires `macos-latest` / `macos-13` GitHub-hosted runners**; will hang on self-hosted-only runner setups that lack macOS runners |
| `build-installer.yml` | Installer-only build matrix |

> **Forgejo self-hosted runner compatibility:** `.forgejo/workflows/` pins `actions/upload-artifact` (and `build-installer.yml`'s `download-artifact`) to **`@v3`** — `@v4` hard-fails on Forgejo/Gitea with `GHESNotSupportedError` since it only talks to github.com's artifact API. `.github/workflows/` uses **`@v4`** instead, since GitHub.com auto-fails any job that still uses the now-deprecated `@v3` artifact actions. The GUI workflows additionally try `actions/setup-python@v5` first and fall back to whatever `python3`/`python` is already on the runner if that action fails (common on Forgejo self-hosted ARM64/proot runners, which can't resolve the GitHub-hosted Python version manifest).
>
> **Release action differs by platform — workflows are duplicated in two folders:** `.github/workflows/` uses `softprops/action-gh-release` (works on real GitHub.com, fails on Forgejo since it requires a direct clone from github.com). `.forgejo/workflows/` uses `actions/forgejo-release` (resolved through Forgejo's `data.forgejo.org` action mirror, works on self-hosted Forgejo, doesn't exist on github.com). Forgejo ignores `.github/workflows/` entirely whenever a `.forgejo/workflows/` folder is present, and GitHub ignores `.forgejo/workflows/` entirely — so each platform only ever sees its own correct copy, with no duplicate runs. **If you change a workflow, update both copies.**


---

## Project Structure

```
forgejo-forge/
├── main.go
├── cmd/                        # CLI subcommands (setup/start/stop/restart/status/logs/email/config/uninstall)
│   ├── config.go               # config path/sections/list/get/set/remove/raw-get/raw-set/enable-actions
│   ├── runner.go               # runner install/register/start/stop/status/uninstall
│   ├── runner_sysproc_unix.go  # detached-process attrs (Linux/macOS)
│   └── runner_sysproc_windows.go # detached-process attrs (Windows)
├── internal/
│   ├── admin/create.go         # admin user create (Forgejo & Gitea compatible)
│   ├── config/                 # app.ini writer, reader, mailer patcher, editor (set/remove/list key=value)
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
├── gui/                        # PyQt6 GUI (incl. app.ini editor dialog + INI syntax highlighter)
└── Makefile
```

---

## License

MIT License — see [LICENSE](LICENSE)
