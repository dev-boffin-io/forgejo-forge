@echo off
setlocal enabledelayedexpansion

:: ════════════════════════════════════════════════════════════════════
::  forgejo-forge  —  Windows build script
::  Usage:  build.bat [target] [arch]
::
::  Targets : all (default)  cli  installer  gui  clean  help
::  Arch    : amd64 (default)  arm64
::
::  Examples:
::    build.bat
::    build.bat all arm64
::    build.bat cli
::    build.bat gui
::    build.bat clean
:: ════════════════════════════════════════════════════════════════════

:: ── Parse arguments ──────────────────────────────────────────────────
set "TARGET=all"
set "ARCH=amd64"

if not "%~1"=="" (
    set "TARGET=%~1"
)
if not "%~2"=="" (
    set "ARCH=%~2"
)

:: Normalise target
if /i "%TARGET%"=="help"      goto :show_help
if /i "%TARGET%"=="clean"     goto :do_clean
if /i "%TARGET%"=="all"       goto :check_prereqs
if /i "%TARGET%"=="cli"       goto :check_prereqs
if /i "%TARGET%"=="installer" goto :check_prereqs
if /i "%TARGET%"=="gui"       goto :check_prereqs

echo [ERROR] Unknown target: %TARGET%
echo Run   build.bat help   for usage.
exit /b 1

:: ── Help ─────────────────────────────────────────────────────────────
:show_help
echo.
echo   forgejo-forge — Windows Build Script
echo.
echo   Usage:  build.bat [target] [arch]
echo.
echo   Targets:
echo     all          Build CLI + Installer + GUI  (default)
echo     cli          Build forgejo-forge-windows-^<arch^>.exe only
echo     installer    Build forgejo-main-windows-^<arch^>.exe only
echo     gui          Build forgejo-forge-gui.exe only  (PyInstaller)
echo     clean        Remove bin\  and  .venv\
echo     help         Show this message
echo.
echo   Arch:
echo     amd64        64-bit Intel/AMD  (default)
echo     arm64        64-bit ARM
echo.
echo   Prerequisites:
echo     Go   1.22+  ^(https://go.dev/dl/^)
echo     Python 3.10+ with pip  ^(https://python.org^) — for gui target
echo.
goto :eof

:: ── Clean ─────────────────────────────────────────────────────────────
:do_clean
echo [CLEAN] Removing bin\ and .venv\ ...
if exist bin   rmdir /s /q bin
if exist .venv rmdir /s /q .venv
if exist .build rmdir /s /q .build
if exist .spec  rmdir /s /q .spec
echo [OK] Clean done.
goto :eof

:: ── Check prerequisites ───────────────────────────────────────────────
:check_prereqs
echo.
echo ════════════════════════════════════════════════════════════════════
echo   forgejo-forge — Windows Build
echo   Target : %TARGET%    Arch : %ARCH%
echo ════════════════════════════════════════════════════════════════════
echo.

:: Go
where go >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Go not found in PATH.
    echo         Download from https://go.dev/dl/
    exit /b 1
)
for /f "tokens=3" %%v in ('go version') do echo [OK] Go %%v

:: Python — only required for gui / all
if /i "%TARGET%"=="gui" goto :need_python
if /i "%TARGET%"=="all" goto :need_python
goto :check_git

:need_python
set "PYTHON="
for %%P in (python python3) do (
    if "!PYTHON!"=="" (
        where %%P >nul 2>&1
        if not errorlevel 1 set "PYTHON=%%P"
    )
)
if "!PYTHON!"=="" (
    echo [ERROR] Python not found in PATH.
    echo         Download from https://python.org
    exit /b 1
)
for /f "tokens=*" %%v in ('!PYTHON! --version 2^>^&1') do echo [OK] %%v

:check_git
:: Git — optional, used for version tag
set "VERSION=dev"
where git >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('git describe --tags --always --dirty 2^>nul') do (
        if not "%%v"=="" set "VERSION=%%v"
    )
)
echo [OK] Version: %VERSION%
echo.

:: Create bin\
if not exist bin mkdir bin

:: ── Dispatch ──────────────────────────────────────────────────────────
if /i "%TARGET%"=="cli"       goto :build_cli
if /i "%TARGET%"=="installer" goto :build_installer
if /i "%TARGET%"=="gui"       goto :build_gui
:: all — fall through
goto :build_cli

:: ── CLI ───────────────────────────────────────────────────────────────
:build_cli
echo [BUILD] CLI  (forgejo-forge-windows-%ARCH%.exe) ...

set "GOOS=windows"
set "GOARCH=%ARCH%"
set "CGO_ENABLED=0"

go mod tidy
if errorlevel 1 ( echo [ERROR] go mod tidy failed & exit /b 1 )

go build -ldflags "-s -w -X main.version=%VERSION%" -o bin\forgejo-forge-windows-%ARCH%.exe .
if errorlevel 1 ( echo [ERROR] CLI build failed & exit /b 1 )

echo [OK] bin\forgejo-forge-windows-%ARCH%.exe

if /i "%TARGET%"=="cli" goto :done
goto :build_installer

:: ── Installer ─────────────────────────────────────────────────────────
:build_installer
echo.
echo [BUILD] Installer  (forgejo-main-windows-%ARCH%.exe) ...

pushd forgejo-installer
if errorlevel 1 ( echo [ERROR] forgejo-installer\ directory not found & exit /b 1 )

set "GOOS=windows"
set "GOARCH=%ARCH%"
set "CGO_ENABLED=0"

go mod tidy
if errorlevel 1 ( popd & echo [ERROR] go mod tidy (installer) failed & exit /b 1 )

go build -ldflags "-s -w" -o ..\bin\forgejo-main-windows-%ARCH%.exe .
if errorlevel 1 ( popd & echo [ERROR] Installer build failed & exit /b 1 )

popd
echo [OK] bin\forgejo-main-windows-%ARCH%.exe

if /i "%TARGET%"=="installer" goto :done
goto :build_gui

:: ── GUI ───────────────────────────────────────────────────────────────
:build_gui
echo.
echo [BUILD] GUI  (forgejo-forge-gui.exe via PyInstaller) ...

if "!PYTHON!"=="" (
    :: Detect python again in case we arrived here from "all"
    set "PYTHON="
    for %%P in (python python3) do (
        if "!PYTHON!"=="" (
            where %%P >nul 2>&1
            if not errorlevel 1 set "PYTHON=%%P"
        )
    )
    if "!PYTHON!"=="" (
        echo [SKIP] Python not found — skipping GUI build.
        goto :done
    )
)

:: Create venv
if not exist .venv (
    echo [VENV] Creating .venv ...
    !PYTHON! -m venv .venv
    if errorlevel 1 ( echo [ERROR] Failed to create venv & exit /b 1 )
)

echo [VENV] Installing pyinstaller + pyqt6 ...
.venv\Scripts\pip install --quiet --upgrade pip pyinstaller pyqt6
if errorlevel 1 ( echo [ERROR] pip install failed & exit /b 1 )

if exist gui\requirements.txt (
    .venv\Scripts\pip install --quiet -r gui\requirements.txt
    if errorlevel 1 ( echo [ERROR] pip install requirements.txt failed & exit /b 1 )
)

echo [PYINSTALLER] Building exe ...
set "ICON_ARG="
if exist gui\forgejo-forge.png (
    set "ICON_ARG=--add-data gui\forgejo-forge.png;."
)

.venv\Scripts\pyinstaller ^
    --onefile ^
    --name forgejo-forge-gui ^
    --distpath bin ^
    --workpath .build ^
    --specpath .spec ^
    --noconsole ^
    %ICON_ARG% ^
    gui\forgejo-forge.py

if errorlevel 1 ( echo [ERROR] PyInstaller failed & exit /b 1 )

:: Cleanup build artifacts (keep .venv for faster rebuilds)
if exist .build rmdir /s /q .build
if exist .spec  rmdir /s /q .spec

echo [OK] bin\forgejo-forge-gui.exe

:: ── Done ─────────────────────────────────────────────────────────────
:done
echo.
echo ════════════════════════════════════════════════════════════════════
echo   Build complete  —  output in bin\
echo.
if exist bin dir /b bin
echo ════════════════════════════════════════════════════════════════════
echo.
