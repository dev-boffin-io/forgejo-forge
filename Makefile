BINARY    := forgejo-forge
MODULE    := github.com/dev-boffin-io/forgejo-forge
VERSION   := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS           := -ldflags "-s -w -X main.version=$(VERSION)"
INSTALLER_LDFLAGS := -ldflags "-s -w"

# Installer sub-project
INSTALLER_DIR    := forgejo-installer
INSTALLER_BINARY := forgejo-main

# GUI
GUI_SRC   := gui/forgejo-forge.py
GUI_ICON  := gui/forgejo-forge.png
GUI_APP   := forgejo-forge-gui

VENV      := .venv
VENV_BIN  := $(VENV)/bin
BUILD_DIR := .build
SPEC_DIR  := .spec

PYTHON   := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)
ICON_ABS := $(shell [ -f $(GUI_ICON) ] && (realpath $(GUI_ICON) 2>/dev/null || readlink -f $(GUI_ICON) 2>/dev/null || echo $(GUI_ICON)))

# Install paths
PREFIX      ?= $(HOME)/.local
BIN_INSTALL := $(PREFIX)/bin
DESKTOP_DIR := $(HOME)/.local/share/applications

.PHONY: help all build build-arm64 build-amd64 build-windows build-windows-arm64 build-all \
        prepare clean check \
        installer installer-arm64 installer-amd64 installer-windows installer-windows-arm64 installer-all \
        gui-build install install-gui install-installer \
        uninstall check-python check-venv-pkg

# ─── Default ────────────────────────────────────────────────────────
all: build installer gui-build

# ─── Python checks ──────────────────────────────────────────────────
check-python:
	@if [ -z "$(PYTHON)" ]; then \
		echo "❌ python3 not found"; exit 1; \
	fi
	@echo "✅ Python: $(PYTHON) ($$($(PYTHON) --version 2>&1))"

check-venv-pkg: check-python
	@if ! $(PYTHON) -m venv --help > /dev/null 2>&1; then \
		echo "❌ python3-venv missing. Run: sudo apt install python3-venv"; exit 1; \
	fi
	@echo "✅ venv module OK"

# ─── Go: Prepare (main project) ─────────────────────────────────────
prepare:
	@rm -rf bin/$(BINARY) bin/$(BINARY)-amd64 bin/$(BINARY)-arm64 go.sum
	@go mod tidy
	@echo "✅ Go deps ready (main)"

# ─── Go: Prepare (installer) ────────────────────────────────────────
prepare-installer:
	@rm -rf bin/$(INSTALLER_BINARY) bin/$(INSTALLER_BINARY)-amd64 bin/$(INSTALLER_BINARY)-arm64
	@cd $(INSTALLER_DIR) && rm -f go.sum && go mod tidy
	@echo "✅ Go deps ready (installer)"

# ─── Go: Build main (native) ────────────────────────────────────────
build: prepare
	@mkdir -p bin
	@go build $(LDFLAGS) -o bin/$(BINARY) .
	@echo "✅ Built → bin/$(BINARY)"

# ─── Go: Build main ARM64 ───────────────────────────────────────────
build-arm64: prepare
	@mkdir -p bin
	@GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o bin/$(BINARY)-arm64 .
	@echo "✅ Built → bin/$(BINARY)-arm64"

# ─── Go: Build main amd64 ───────────────────────────────────────────
build-amd64: prepare
	@mkdir -p bin
	@GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o bin/$(BINARY)-amd64 .
	@echo "✅ Built → bin/$(BINARY)-amd64"

# ─── Go: Build Windows amd64 ────────────────────────────────────────
build-windows: prepare
	@mkdir -p bin
	@GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o bin/$(BINARY)-windows-amd64.exe .
	@echo "✅ Built → bin/$(BINARY)-windows-amd64.exe"

# ─── Go: Build Windows arm64 ────────────────────────────────────────
build-windows-arm64: prepare
	@mkdir -p bin
	@GOOS=windows GOARCH=arm64 go build $(LDFLAGS) -o bin/$(BINARY)-windows-arm64.exe .
	@echo "✅ Built → bin/$(BINARY)-windows-arm64.exe"

# ─── Go: Build main all ─────────────────────────────────────────────
build-all: prepare
	@mkdir -p bin
	@GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o bin/$(BINARY)-amd64 .
	@GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o bin/$(BINARY)-arm64 .
	@GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o bin/$(BINARY)-windows-amd64.exe .
	@GOOS=windows GOARCH=arm64 go build $(LDFLAGS) -o bin/$(BINARY)-windows-arm64.exe .
	@echo "✅ Built all platforms → bin/"

# ─── Go: Build installer (native) ───────────────────────────────────
installer: prepare-installer
	@mkdir -p bin
	@cd $(INSTALLER_DIR) && go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY) .
	@echo "✅ Built → bin/$(INSTALLER_BINARY)"

# ─── Go: Build installer ARM64 ──────────────────────────────────────
installer-arm64: prepare-installer
	@mkdir -p bin
	@cd $(INSTALLER_DIR) && GOOS=linux GOARCH=arm64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-arm64 .
	@echo "✅ Built → bin/$(INSTALLER_BINARY)-arm64"

# ─── Go: Build installer amd64 ──────────────────────────────────────
installer-amd64: prepare-installer
	@mkdir -p bin
	@cd $(INSTALLER_DIR) && GOOS=linux GOARCH=amd64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-amd64 .
	@echo "✅ Built → bin/$(INSTALLER_BINARY)-amd64"

# ─── Go: Build installer Windows amd64 ─────────────────────────────
installer-windows: prepare-installer
	@mkdir -p bin
	@cd $(INSTALLER_DIR) && GOOS=windows GOARCH=amd64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-windows-amd64.exe .
	@echo "✅ Built → bin/$(INSTALLER_BINARY)-windows-amd64.exe"

# ─── Go: Build installer Windows arm64 ─────────────────────────────
installer-windows-arm64: prepare-installer
	@mkdir -p bin
	@cd $(INSTALLER_DIR) && GOOS=windows GOARCH=arm64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-windows-arm64.exe .
	@echo "✅ Built → bin/$(INSTALLER_BINARY)-windows-arm64.exe"

# ─── Go: Build installer all ────────────────────────────────────────
installer-all: prepare-installer
	@mkdir -p bin
	@cd $(INSTALLER_DIR) && GOOS=linux GOARCH=amd64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-amd64 .
	@cd $(INSTALLER_DIR) && GOOS=linux GOARCH=arm64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-arm64 .
	@cd $(INSTALLER_DIR) && GOOS=windows GOARCH=amd64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-windows-amd64.exe .
	@cd $(INSTALLER_DIR) && GOOS=windows GOARCH=arm64 go build $(INSTALLER_LDFLAGS) -o ../bin/$(INSTALLER_BINARY)-windows-arm64.exe .
	@echo "✅ Built installer all platforms → bin/"

# ─── Go: Vet ────────────────────────────────────────────────────────
check: prepare
	@go vet ./...
	@cd $(INSTALLER_DIR) && go vet ./...
	@echo "✅ Vet passed"

# ─── GUI: venv setup ────────────────────────────────────────────────
$(VENV): check-venv-pkg
	@rm -rf $(VENV)
	@echo "📦 Creating virtualenv..."
	@$(PYTHON) -m venv $(VENV)
	@$(VENV_BIN)/pip install --quiet --upgrade pip pyinstaller pyqt6
	@if [ -f gui/requirements.txt ]; then \
		echo "📥 Installing gui/requirements.txt..."; \
		$(VENV_BIN)/pip install --quiet -r gui/requirements.txt; \
	fi
	@echo "✅ venv ready"

# ─── GUI: Build (PyInstaller → bin/forgejo-forge-gui) ─────────────────
gui-build: $(VENV)
	@mkdir -p bin
	@rm -f bin/$(GUI_APP)
	@echo "🔨 Building GUI → bin/$(GUI_APP)..."
	@$(VENV_BIN)/pyinstaller \
		--onefile \
		--strip \
		--name $(GUI_APP) \
		--distpath bin \
		--workpath $(BUILD_DIR) \
		--specpath $(SPEC_DIR) \
		$(if $(ICON_ABS),--add-data "$(ICON_ABS):.",) \
		$(GUI_SRC)
	@rm -rf $(VENV) $(BUILD_DIR) $(SPEC_DIR) __pycache__ *.pyc *.pyo
	@echo "✅ Built → bin/$(GUI_APP)"

# ─── Install: Go CLI binary ─────────────────────────────────────────
install:
	@if [ ! -f bin/$(BINARY) ]; then \
		echo "❌ bin/$(BINARY) not found. Run 'make build' first."; exit 1; \
	fi
	@mkdir -p $(BIN_INSTALL)
	@ln -sf "$$(realpath bin/$(BINARY) 2>/dev/null || readlink -f bin/$(BINARY))" \
		$(BIN_INSTALL)/$(BINARY)
	@echo "✅ Symlink → $(BIN_INSTALL)/$(BINARY)"

# ─── Install: Installer binary ──────────────────────────────────────
install-installer:
	@if [ ! -f bin/$(INSTALLER_BINARY) ]; then \
		echo "❌ bin/$(INSTALLER_BINARY) not found. Run 'make installer' first."; exit 1; \
	fi
	@mkdir -p $(BIN_INSTALL)
	@ln -sf "$$(realpath bin/$(INSTALLER_BINARY) 2>/dev/null || readlink -f bin/$(INSTALLER_BINARY))" \
		$(BIN_INSTALL)/$(INSTALLER_BINARY)
	@echo "✅ Symlink → $(BIN_INSTALL)/$(INSTALLER_BINARY)"

# ─── Install: GUI binary + desktop entry ────────────────────────────
install-gui:
	@if [ ! -f bin/$(GUI_APP) ]; then \
		echo "❌ bin/$(GUI_APP) not found. Run 'make gui-build' first."; exit 1; \
	fi
	@mkdir -p $(BIN_INSTALL)
	@ln -sf "$$(realpath bin/$(GUI_APP) 2>/dev/null || readlink -f bin/$(GUI_APP))" \
		$(BIN_INSTALL)/$(GUI_APP)
	@echo "✅ Symlink → $(BIN_INSTALL)/$(GUI_APP)"
	@mkdir -p $(DESKTOP_DIR)
	@printf '[Desktop Entry]\nName=Forgejo Forge\nExec="%s"\nType=Application\nTerminal=false\nCategories=Network;Development;\n%s\n' \
		"$(BIN_INSTALL)/$(GUI_APP)" \
		"$(if $(ICON_ABS),Icon=$(ICON_ABS),)" \
		> $(DESKTOP_DIR)/$(GUI_APP).desktop
	@chmod 644 $(DESKTOP_DIR)/$(GUI_APP).desktop
	@echo "✅ Desktop entry → $(DESKTOP_DIR)/$(GUI_APP).desktop"
	@if ! echo "$$PATH" | grep -q "$(BIN_INSTALL)"; then \
		echo "⚠️  Add $(BIN_INSTALL) to PATH"; \
	fi
	@echo "🚀 GUI install complete"

# ─── Uninstall: all ─────────────────────────────────────────────────
uninstall:
	@rm -f $(BIN_INSTALL)/$(BINARY)
	@rm -f $(BIN_INSTALL)/$(INSTALLER_BINARY)
	@rm -f $(BIN_INSTALL)/$(GUI_APP)
	@rm -f $(DESKTOP_DIR)/$(GUI_APP).desktop
	@echo "✅ Uninstalled $(BINARY) + $(INSTALLER_BINARY) + $(GUI_APP)"

# ─── Clean everything ───────────────────────────────────────────────
clean:
	@rm -rf bin/ go.sum $(INSTALLER_DIR)/go.sum \
		$(VENV) $(BUILD_DIR) $(SPEC_DIR) __pycache__ *.pyc *.pyo *.spec
	@echo "🧹 Clean done"

# ─── Help ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  forgejo-forge — Makefile targets"
	@echo ""
	@echo "  ── Go CLI ──────────────────────────────────────────────"
	@echo "  build                  Build bin/forgejo-forge (native)"
	@echo "  build-amd64            Build bin/forgejo-forge-amd64"
	@echo "  build-arm64            Build bin/forgejo-forge-arm64"
	@echo "  build-windows          Build bin/forgejo-forge-windows-amd64.exe"
	@echo "  build-windows-arm64    Build bin/forgejo-forge-windows-arm64.exe"
	@echo "  build-all              Build all platforms"
	@echo ""
	@echo "  ── Installer ───────────────────────────────────────────"
	@echo "  installer              Build bin/forgejo-main (native)"
	@echo "  installer-amd64        Build bin/forgejo-main-amd64"
	@echo "  installer-arm64        Build bin/forgejo-main-arm64"
	@echo "  installer-windows      Build bin/forgejo-main-windows-amd64.exe"
	@echo "  installer-windows-arm64 Build bin/forgejo-main-windows-arm64.exe"
	@echo "  installer-all          Build installer all platforms"
	@echo ""
	@echo "  ── GUI ─────────────────────────────────────────────────"
	@echo "  gui-build              Build bin/forgejo-forge-gui (PyInstaller)"
	@echo ""
	@echo "  ── Install ─────────────────────────────────────────────"
	@echo "  install                Symlink forgejo-forge → ~/.local/bin/"
	@echo "  install-installer      Symlink forgejo-main  → ~/.local/bin/"
	@echo "  install-gui            Symlink forgejo-forge-gui + .desktop entry"
	@echo "  uninstall              Remove all symlinks + desktop entry"
	@echo ""
	@echo "  ── Other ───────────────────────────────────────────────"
	@echo "  all                    build + installer + gui-build"
	@echo "  check                  go vet (main + installer)"
	@echo "  clean                  Remove bin/, go.sum, venv, build artifacts"
	@echo "  help                   Show this message"
	@echo ""
