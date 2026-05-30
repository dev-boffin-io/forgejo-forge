#Requires -Version 5.1
<#
.SYNOPSIS
    Build script for forgejo-forge on Windows.

.DESCRIPTION
    Builds the CLI, installer, and/or GUI (PyInstaller) binaries.
    Run from the repository root.

.PARAMETER Target
    What to build: all | cli | installer | gui | clean | help
    Default: all

.PARAMETER Arch
    Target architecture: amd64 | arm64
    Default: amd64

.PARAMETER SkipGUI
    Skip the PyInstaller GUI build even when Target is "all".

.EXAMPLE
    .\build.ps1
    .\build.ps1 -Target cli
    .\build.ps1 -Target all -Arch arm64
    .\build.ps1 -Target gui
    .\build.ps1 -Target clean
#>

param(
    [ValidateSet("all", "cli", "installer", "gui", "clean", "help")]
    [string]$Target = "all",

    [ValidateSet("amd64", "arm64")]
    [string]$Arch = "amd64",

    [switch]$SkipGUI
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours ───────────────────────────────────────────────────────────
function Write-Ok    ($msg) { Write-Host "  [OK] $msg"    -ForegroundColor Green  }
function Write-Info  ($msg) { Write-Host "  [..] $msg"    -ForegroundColor Cyan   }
function Write-Warn  ($msg) { Write-Host "  [!!] $msg"    -ForegroundColor Yellow }
function Write-Err   ($msg) { Write-Host "  [ERROR] $msg" -ForegroundColor Red    }
function Write-Head  ($msg) {
    Write-Host ""
    Write-Host ("═" * 68) -ForegroundColor DarkGray
    Write-Host "  $msg"   -ForegroundColor White
    Write-Host ("═" * 68) -ForegroundColor DarkGray
    Write-Host ""
}
function Write-Step  ($msg) { Write-Host "`n  ── $msg" -ForegroundColor Magenta }

# ── Help ──────────────────────────────────────────────────────────────
function Show-Help {
    Write-Host @"

  forgejo-forge — PowerShell Build Script

  Usage:  .\build.ps1 [-Target <target>] [-Arch <arch>] [-SkipGUI]

  Targets:
    all          Build CLI + Installer + GUI  (default)
    cli          Build forgejo-forge-windows-<arch>.exe only
    installer    Build forgejo-main-windows-<arch>.exe only
    gui          Build forgejo-forge-gui.exe  (PyInstaller)
    clean        Remove bin\  and  .venv\
    help         Show this message

  Arch:
    amd64        64-bit Intel/AMD  (default)
    arm64        64-bit ARM

  Flags:
    -SkipGUI     Skip GUI build even when Target is "all"

  Prerequisites:
    Go   1.22+     https://go.dev/dl/
    Python 3.10+   https://python.org   (gui / all targets only)

  Examples:
    .\build.ps1
    .\build.ps1 -Target cli
    .\build.ps1 -Target all -Arch arm64
    .\build.ps1 -Target gui
    .\build.ps1 -SkipGUI
    .\build.ps1 -Target clean

"@
}

# ── Clean ─────────────────────────────────────────────────────────────
function Invoke-Clean {
    Write-Step "Cleaning build artifacts"
    foreach ($dir in @("bin", ".venv", ".build", ".spec")) {
        if (Test-Path $dir) {
            Remove-Item $dir -Recurse -Force
            Write-Ok "Removed $dir\"
        }
    }
    Write-Ok "Clean done."
}

# ── Check prerequisites ───────────────────────────────────────────────
function Find-Command ([string]$name) {
    return (Get-Command $name -ErrorAction SilentlyContinue)
}

function Assert-Go {
    $go = Find-Command "go"
    if (-not $go) {
        Write-Err "Go not found in PATH.`n         Download from https://go.dev/dl/"
        exit 1
    }
    $ver = (& go version) -replace "^go version ", ""
    Write-Ok "Go  $ver"
}

function Find-Python {
    foreach ($name in @("python", "python3")) {
        $cmd = Find-Command $name
        if ($cmd) {
            $ver = (& $cmd.Source --version 2>&1)
            if ($ver -match "Python 3") {
                Write-Ok "$ver  ($($cmd.Source))"
                return $cmd.Source
            }
        }
    }
    return $null
}

function Get-Version {
    try {
        $v = (git describe --tags --always --dirty 2>$null)
        if ($v) { return $v.Trim() }
    } catch {}
    return "dev"
}

# ── Go build helper ───────────────────────────────────────────────────
function Invoke-GoBuild {
    param(
        [string]$Label,
        [string]$WorkDir,
        [string]$Output,
        [string]$LDFlags,
        [string]$GoOS   = "windows",
        [string]$GoArch = $Arch
    )

    Write-Step "Building $Label"

    $savedDir = $PWD
    if ($WorkDir) { Set-Location $WorkDir }

    try {
        $env:GOOS        = $GoOS
        $env:GOARCH      = $GoArch
        $env:CGO_ENABLED = "0"

        Write-Info "go mod tidy ..."
        & go mod tidy
        if ($LASTEXITCODE -ne 0) { throw "go mod tidy failed" }

        $outPath = if ($WorkDir) { Join-Path ".." $Output } else { $Output }
        Write-Info "go build → $Output"
        & go build -ldflags $LDFlags -o $outPath .
        if ($LASTEXITCODE -ne 0) { throw "go build failed" }

        Write-Ok $Output
    } finally {
        Set-Location $savedDir
        # Restore env
        Remove-Item Env:\GOOS        -ErrorAction SilentlyContinue
        Remove-Item Env:\GOARCH      -ErrorAction SilentlyContinue
        Remove-Item Env:\CGO_ENABLED -ErrorAction SilentlyContinue
    }
}

# ── GUI build ─────────────────────────────────────────────────────────
function Invoke-GUIBuild ([string]$pythonExe) {
    Write-Step "Building GUI  (PyInstaller → bin\forgejo-forge-gui.exe)"

    # Venv
    $venvPip        = ".venv\Scripts\pip.exe"
    $venvPyInstaller = ".venv\Scripts\pyinstaller.exe"

    if (-not (Test-Path ".venv")) {
        Write-Info "Creating .venv ..."
        & $pythonExe -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
    }

    Write-Info "Installing pyinstaller + pyqt6 ..."
    & $venvPip install --quiet --upgrade pip pyinstaller pyqt6
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

    if (Test-Path "gui\requirements.txt") {
        & $venvPip install --quiet -r gui\requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "pip install requirements.txt failed" }
    }

    # Build icon add-data arg (Windows uses ; as separator)
    $addDataArgs = @()
    if (Test-Path "gui\forgejo-forge.png") {
        $iconAbs = (Resolve-Path "gui\forgejo-forge.png").Path
        $addDataArgs = @("--add-data", "$iconAbs;.")
    }

    Write-Info "Running pyinstaller ..."
    $psArgs = @(
        "--onefile",
        "--name", "forgejo-forge-gui",
        "--distpath", "bin",
        "--workpath", ".build",
        "--specpath", ".spec",
        "--noconsole"
    ) + $addDataArgs + @("gui\forgejo-forge.py")

    & $venvPyInstaller @psArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

    # Clean build artifacts (keep .venv for faster rebuilds)
    foreach ($dir in @(".build", ".spec")) {
        if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
    }

    Write-Ok "bin\forgejo-forge-gui.exe"
}

# ── Summary ───────────────────────────────────────────────────────────
function Show-Summary {
    Write-Host ""
    Write-Host ("═" * 68) -ForegroundColor DarkGray
    Write-Host "  Build complete  —  output in bin\" -ForegroundColor Green
    Write-Host ""
    if (Test-Path "bin") {
        Get-ChildItem "bin" | ForEach-Object {
            $size = "{0,8:N0} KB" -f ($_.Length / 1KB)
            Write-Host ("    {0,-45} {1}" -f $_.Name, $size) -ForegroundColor Cyan
        }
    }
    Write-Host ("═" * 68) -ForegroundColor DarkGray
    Write-Host ""
}

# ════════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════════

if ($Target -eq "help") { Show-Help; exit 0 }
if ($Target -eq "clean") { Invoke-Clean; exit 0 }

# Validate repo root
if (-not (Test-Path "go.mod")) {
    Write-Err "go.mod not found. Run this script from the repository root."
    exit 1
}

Write-Head "forgejo-forge — Windows Build   Target=$Target   Arch=$Arch"

# Check Go
Assert-Go

# Check Python (only needed for gui / all-without-SkipGUI)
$pythonExe = $null
$needsPython = ($Target -eq "gui") -or ($Target -eq "all" -and -not $SkipGUI)
if ($needsPython) {
    $pythonExe = Find-Python
    if (-not $pythonExe) {
        if ($Target -eq "gui") {
            Write-Err "Python 3 not found. Install from https://python.org"
            exit 1
        } else {
            Write-Warn "Python not found — GUI build will be skipped."
        }
    }
}

# Version
$version = Get-Version
Write-Ok "Version: $version"

# Ensure bin\ exists
if (-not (Test-Path "bin")) { New-Item -ItemType Directory -Path "bin" | Out-Null }

$cliOut       = "bin\forgejo-forge-windows-$Arch.exe"
$installerOut = "bin\forgejo-main-windows-$Arch.exe"
$ldFlags      = "-s -w -X main.version=$version"
$instLdFlags  = "-s -w"

try {
    switch ($Target) {
        "cli" {
            Invoke-GoBuild -Label "CLI" -Output $cliOut -LDFlags $ldFlags
        }
        "installer" {
            Invoke-GoBuild -Label "Installer" -WorkDir "forgejo-installer" `
                           -Output $installerOut -LDFlags $instLdFlags
        }
        "gui" {
            if (-not $pythonExe) {
                Write-Err "Python 3 required for gui target."
                exit 1
            }
            Invoke-GUIBuild $pythonExe
        }
        "all" {
            Invoke-GoBuild -Label "CLI" -Output $cliOut -LDFlags $ldFlags
            Invoke-GoBuild -Label "Installer" -WorkDir "forgejo-installer" `
                           -Output $installerOut -LDFlags $instLdFlags
            if ($pythonExe -and -not $SkipGUI) {
                Invoke-GUIBuild $pythonExe
            } elseif ($SkipGUI) {
                Write-Warn "GUI skipped (-SkipGUI)"
            } else {
                Write-Warn "GUI skipped (Python not found)"
            }
        }
    }
} catch {
    Write-Err $_
    exit 1
}

Show-Summary
