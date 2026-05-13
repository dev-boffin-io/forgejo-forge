package detect

import (
	"os"
	"os/exec"
	"runtime"
)

type Mode string

const (
	ModeSystemd Mode = "systemd"
	ModeProot   Mode = "proot"
	ModeWindows Mode = "windows"
)

// Env returns the current runtime mode.
// Windows → ModeWindows, Linux with systemd → ModeSystemd, else → ModeProot.
func Env() Mode {
	if runtime.GOOS == "windows" {
		return ModeWindows
	}
	if _, err := exec.LookPath("systemctl"); err != nil {
		return ModeProot
	}
	if _, err := os.Stat("/run/systemd/system"); err != nil {
		return ModeProot
	}
	return ModeSystemd
}

// ForgejoBin returns the path to the git forge binary in PATH.
//
//	Linux  → looks for "forgejo"
//	Windows → looks for "gitea.exe" / "gitea" (Forgejo dropped Windows support)
func ForgejoBin() string {
	var candidates []string
	if runtime.GOOS == "windows" {
		candidates = []string{"gitea.exe", "gitea"}
	} else {
		candidates = []string{"forgejo"}
	}
	for _, name := range candidates {
		if path, err := exec.LookPath(name); err == nil {
			return path
		}
	}
	return ""
}

// BinaryName returns the short name of the binary for the current OS.
func BinaryName() string {
	if runtime.GOOS == "windows" {
		return "gitea"
	}
	return "forgejo"
}
