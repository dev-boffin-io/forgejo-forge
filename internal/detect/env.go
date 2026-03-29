package detect

import (
	"os"
	"os/exec"
)

type Mode string

const (
	ModeSystemd Mode = "systemd"
	ModeProot   Mode = "proot"
)

// Env returns ModeSystemd if systemctl is available and /run/systemd/system
// exists, otherwise ModeProot.
func Env() Mode {
	if _, err := exec.LookPath("systemctl"); err != nil {
		return ModeProot
	}
	if _, err := os.Stat("/run/systemd/system"); err != nil {
		return ModeProot
	}
	return ModeSystemd
}

// ForgejoBin returns the full path to the gitea binary or an empty string.
func ForgejoBin() string {
	path, err := exec.LookPath("forgejo")
	if err != nil {
		return ""
	}
	return path
}
