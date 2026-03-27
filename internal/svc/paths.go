package svc

import (
	"os/user"
	"path/filepath"

	"github.com/dev-boffin-io/gitea-forge/internal/detect"
)

// Paths holds all filesystem paths for a given mode.
type Paths struct {
	IniPath    string
	LogFile    string
	BaseDir    string // proot only; empty for systemd
	SystemdUnit string // systemd only
}

// Resolve returns the canonical Paths for the current environment mode.
func Resolve(mode detect.Mode) (Paths, error) {
	switch mode {
	case detect.ModeSystemd:
		return Paths{
			IniPath:     "/etc/gitea/app.ini",
			LogFile:     "", // journalctl handles logs
			SystemdUnit: "gitea",
		}, nil
	default: // proot
		u, err := user.Current()
		if err != nil {
			return Paths{}, err
		}
		base := filepath.Join(u.HomeDir, "forge-storage", "gitea")
		return Paths{
			IniPath: filepath.Join(base, "custom", "conf", "app.ini"),
			LogFile: filepath.Join(base, "data", "log", "gitea.log"),
			BaseDir: base,
		}, nil
	}
}
