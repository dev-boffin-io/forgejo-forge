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

// GiteaBin returns the full path to the gitea binary or an empty string.
func GiteaBin() string {
	path, err := exec.LookPath("gitea")
	if err != nil {
		return ""
	}
	return path
}
