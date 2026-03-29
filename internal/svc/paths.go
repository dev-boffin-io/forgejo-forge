package svc

import (
	"os/user"
	"path/filepath"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
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
			IniPath:     "/etc/forgejo/app.ini",
			LogFile:     "", // journalctl handles logs
			SystemdUnit: "forgejo",
		}, nil
	default: // proot
		u, err := user.Current()
		if err != nil {
			return Paths{}, err
		}
		base := filepath.Join(u.HomeDir, "forge-storage", "forgejo")
		return Paths{
			IniPath: filepath.Join(base, "custom", "conf", "app.ini"),
			LogFile: filepath.Join(base, "data", "log", "forgejo.log"),
			BaseDir: base,
		}, nil
	}
}
