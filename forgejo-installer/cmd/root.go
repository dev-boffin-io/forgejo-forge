package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/dev-boffin-io/forgejo-installer/internal/arch"
	"github.com/dev-boffin-io/forgejo-installer/internal/download"
	"github.com/dev-boffin-io/forgejo-installer/internal/install"
	"github.com/dev-boffin-io/forgejo-installer/internal/version"
)

// ── ANSI colours ──────────────────────────────────────────────────────────────
const (
	green  = "\033[1;32m"
	red    = "\033[1;31m"
	yellow = "\033[1;33m"
	cyan   = "\033[1;36m"
	blue   = "\033[1;34m"
	reset  = "\033[0m"
)

func colorize(color, msg string) string { return color + msg + reset }

// ── Entry point ───────────────────────────────────────────────────────────────

func Run(args []string) {
	if len(args) < 1 {
		usage()
		os.Exit(1)
	}

	action := args[0]
	info := arch.Primary()

	fmt.Println(colorize(cyan, "─── Forge Installer ─────────────────────────────────"))
	fmt.Printf("  OS           : %s/%s\n", runtime.GOOS, runtime.GOARCH)
	fmt.Printf("  Binary       : %s\n", sourceDisplay(info.Source))
	fmt.Printf("  Arch suffix  : %s\n", info.Suffix)

	latestVer, err := version.LatestForSource(info.Source)
	if err != nil {
		fatalf("Cannot fetch latest version: %v\n", err)
	}

	installedVer := version.Installed()

	fmt.Printf("  Latest       : %s\n", latestVer)
	fmt.Printf("  Installed    : %s\n", installedVer)
	fmt.Printf("  Install path : %s\n", install.Destination(info.Source))
	fmt.Println(colorize(cyan, "─────────────────────────────────────────────────────"))
	fmt.Println()

	if runtime.GOOS == "windows" {
		fmt.Println(colorize(yellow, "  ℹ Windows: using Gitea (Forgejo dropped Windows support in 2024)"))
		fmt.Println()
	}

	switch action {
	case "install":
		runInstall(installedVer, latestVer, info)
	case "update", "upgrade":
		runUpdate(installedVer, latestVer, info)
	case "uninstall", "remove":
		runUninstall(installedVer, info)
	default:
		usage()
		os.Exit(1)
	}
}

// ── Subcommands ───────────────────────────────────────────────────────────────

func runInstall(installedVer, latestVer string, info arch.BinaryInfo) {
	if installedVer != "none" {
		fmt.Println(colorize(yellow, "Already installed. Use 'update' to upgrade."))
		return
	}
	installVersion(latestVer, info)
}

func runUpdate(installedVer, latestVer string, info arch.BinaryInfo) {
	if installedVer == "none" {
		fatalf("Not installed. Run 'install' first.\n")
	}
	if installedVer == latestVer {
		fmt.Printf("%s\n", colorize(green, "Already on the latest version ("+latestVer+")."))
		return
	}
	fmt.Printf("  Updating %s → %s\n\n", installedVer, latestVer)
	installVersion(latestVer, info)
}

func runUninstall(installedVer string, info arch.BinaryInfo) {
	if installedVer == "none" {
		fmt.Println(colorize(yellow, "Not installed. Nothing to remove."))
		return
	}

	fmt.Printf("  Installed version : %s\n", installedVer)
	fmt.Printf("  Binary            : %s\n", info.Source)
	fmt.Print("  Are you sure you want to uninstall? (y/N): ")
	var input string
	fmt.Scanln(&input)

	if input != "y" && input != "Y" {
		fmt.Println(colorize(yellow, "Aborted."))
		return
	}

	if err := install.RemoveBinary(info.Source); err != nil {
		fatalf("Uninstall failed: %v\n", err)
	}

	fmt.Printf("%s\n", colorize(green, "  ✓ "+info.Source+" uninstalled successfully"))
}

// ── Core install logic ────────────────────────────────────────────────────────

func installVersion(ver string, primary arch.BinaryInfo) {
	fallbacks := arch.Fallbacks(primary)

	for _, info := range fallbacks {
		url := download.AssetURL(info.Source, ver, info.Suffix)

		fmt.Printf("  Trying %-35s\n    %s\n", info.Suffix, url)

		if !download.Exists(url) {
			fmt.Println(colorize(red, "  → Not available, skipping."))
			continue
		}

		tmpPath, err := download.ToFile(url, os.Stderr)
		if err != nil {
			fmt.Printf("%s\n", colorize(red, "  → Download failed: "+err.Error()))
			continue
		}

		cleanup := func() { os.Remove(tmpPath) }

		if err := install.ValidateBinary(tmpPath); err != nil {
			fmt.Printf("%s\n", colorize(red, "  → Binary self-test failed: "+err.Error()))
			cleanup()
			continue
		}

		if err := install.MoveToDest(tmpPath, info.Source); err != nil {
			fmt.Printf("%s\n", colorize(red, "  → Install failed: "+err.Error()))
			cleanup()
			continue
		}

		dest := install.Destination(info.Source)
		fmt.Printf("\n%s\n",
			colorize(green, fmt.Sprintf("  ✓ %s %s installed (%s) → %s",
				info.Source, ver, info.Suffix, dest)))

		if runtime.GOOS == "windows" {
			printWindowsPathHint(dest)
		}
		return
	}

	fatalf("All attempts failed. Could not install %s %s.\n", primary.Source, ver)
}

// ── Helpers ───────────────────────────────────────────────────────────────────

func sourceDisplay(source string) string {
	switch source {
	case "gitea":
		return "Gitea  (dl.gitea.com / github.com/go-gitea/gitea)"
	default:
		return "Forgejo (codeberg.org/forgejo/forgejo)"
	}
}

func printWindowsPathHint(dest string) {
	dir := filepath.Dir(dest)
	fmt.Println()
	fmt.Println(colorize(yellow, "  ⚠ Add the following directory to your PATH:"))
	fmt.Printf("    %s\n", dir)
	fmt.Println("  System Properties → Advanced → Environment Variables → Path → Edit")
}

func usage() {
	fmt.Println("Usage: forgejo-main <install|update|upgrade|uninstall>")
	fmt.Println()
	fmt.Println("  Linux          → installs Forgejo  (codeberg.org)")
	fmt.Println("  Windows/macOS  → installs Gitea    (dl.gitea.com)")
}

func fatalf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, colorize(red, "Error: ")+format, args...)
	os.Exit(1)
}
