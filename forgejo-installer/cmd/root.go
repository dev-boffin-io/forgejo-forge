package cmd

import (
	"fmt"
	"os"

	"github.com/dev-boffin-io/forgejo-installer/internal/arch"
	"github.com/dev-boffin-io/forgejo-installer/internal/download"
	"github.com/dev-boffin-io/forgejo-installer/internal/install"
	"github.com/dev-boffin-io/forgejo-installer/internal/version"
)

// ─── ANSI colours ────────────────────────────────────────────────────────────

const (
	green  = "\033[1;32m"
	red    = "\033[1;31m"
	yellow = "\033[1;33m"
	cyan   = "\033[1;36m"
	reset  = "\033[0m"
)

func colorize(color, msg string) string { return color + msg + reset }

// ─── Public entry point ───────────────────────────────────────────────────────

func Run(args []string) {
	if len(args) < 1 {
		usage()
		os.Exit(1)
	}

	action := args[0]

	fmt.Println(colorize(cyan, "─── Forgejo Installer ───────────────────────────────"))
	fmt.Printf("  Primary arch : %s\n", arch.Primary())

	latestVer, err := version.Latest()
	if err != nil {
		fatalf("Cannot fetch latest version: %v\n", err)
	}

	installedVer := version.Installed()

	fmt.Printf("  Latest       : %s\n", latestVer)
	fmt.Printf("  Installed    : %s\n", installedVer)
	fmt.Println(colorize(cyan, "───────────────────────────────────────────────────"))
	fmt.Println()

	switch action {
	case "install":
		runInstall(installedVer, latestVer)
	case "update", "upgrade":
		runUpdate(installedVer, latestVer)
	case "uninstall", "remove":
		runUninstall(installedVer)
	default:
		usage()
		os.Exit(1)
	}
}

// ─── Subcommands ─────────────────────────────────────────────────────────────

func runInstall(installedVer, latestVer string) {
	if installedVer != "none" {
		fmt.Println(colorize(yellow, "Forgejo is already installed. Use 'update' to upgrade."))
		return
	}
	installVersion(latestVer)
}

func runUpdate(installedVer, latestVer string) {
	if installedVer == "none" {
		fatalf("Forgejo is not installed. Run 'install' first.\n")
	}
	if installedVer == latestVer {
		fmt.Printf("%s\n", colorize(green, "Already on the latest version ("+latestVer+")."))
		return
	}
	fmt.Printf("  Updating %s → %s\n\n", installedVer, latestVer)
	installVersion(latestVer)
}

func runUninstall(installedVer string) {
	if installedVer == "none" {
		fmt.Println(colorize(yellow, "Forgejo is not installed. Nothing to remove."))
		return
	}

	fmt.Printf("  Installed version: %s\n", installedVer)

	fmt.Print("  Are you sure you want to uninstall Forgejo? (y/N): ")
	var input string
	fmt.Scanln(&input)

	if input != "y" && input != "Y" {
		fmt.Println(colorize(yellow, "Aborted."))
		return
	}

	if err := install.RemoveBinary(); err != nil {
		fatalf("Uninstall failed: %v\n", err)
	}

	fmt.Println(colorize(green, "  ✓ Gitea uninstalled successfully"))
}

// ─── Core install logic ───────────────────────────────────────────────────────

func installVersion(ver string) {
	primary := arch.Primary()
	arches := arch.Fallbacks(primary)

	for _, a := range arches {
		url := download.AssetURL(ver, a)

		fmt.Printf("  Trying %-20s %s\n", a, url)

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

		if err := install.MoveToDest(tmpPath); err != nil {
			fmt.Printf("%s\n", colorize(red, "  → Install failed: "+err.Error()))
			cleanup()
			continue
		}

		fmt.Printf("\n%s\n",
			colorize(green, fmt.Sprintf("  ✓ Forgejo %s installed (%s) → %s", ver, a, install.Destination())))
		return
	}

	fatalf("All architectures failed. Forgejo %s could not be installed.\n", ver)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

func usage() {
	fmt.Println("Usage: forgejo-installer <install|update|upgrade|uninstall>")
}

func fatalf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, colorize(red, "Error: ")+format, args...)
	os.Exit(1)
}
