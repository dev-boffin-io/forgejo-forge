package config

import (
	"fmt"
	"os"
	"path/filepath"
)

// SystemdParams holds values for the systemd app.ini template.
type SystemdParams struct {
	RunUser  string
	WorkPath string
	DBPath   string
	RepoRoot string
	Port     int
	RootURL  string
	LogPath  string
}

// ProotParams holds values for the proot app.ini template.
type ProotParams struct {
	RunUser  string
	WorkPath string
	DBPath   string
	RepoRoot string
	Port     int
	RootURL  string
	LogPath  string
}

// WriteSystemd writes /etc/forgejo/app.ini for systemd mode.
// INSTALL_LOCK = true so gitea admin user create works immediately.
// Returns (written bool, error). written=false means file already existed.
func WriteSystemd(iniPath string, p SystemdParams) (bool, error) {
	if _, err := os.Stat(iniPath); err == nil {
		return false, nil
	}
	return writeINI(iniPath, fmt.Sprintf(`APP_NAME  = forgejo
RUN_USER  = %s
WORK_PATH = %s

[database]
DB_TYPE = sqlite3
PATH    = %s

[repository]
ROOT = %s

[server]
HTTP_PORT = %d
ROOT_URL  = %s
DOMAIN    = localhost

[packages]
ENABLED = true

[log]
ROOT_PATH = %s

[security]
INSTALL_LOCK = true
SECRET_KEY   = AUTO
`, p.RunUser, p.WorkPath, p.DBPath, p.RepoRoot, p.Port, p.RootURL, p.LogPath))
}

// WriteProot writes the proot app.ini.
// INSTALL_LOCK = true so gitea admin user create works immediately.
// Returns (written bool, error). written=false means file already existed.
func WriteProot(iniPath string, p ProotParams) (bool, error) {
	if _, err := os.Stat(iniPath); err == nil {
		return false, nil
	}
	return writeINI(iniPath, fmt.Sprintf(`APP_NAME  = Forgejo Forge
RUN_USER  = %s
WORK_PATH = %s

[database]
DB_TYPE = sqlite3
PATH    = %s

[repository]
ROOT = %s

[server]
HTTP_PORT   = %d
ROOT_URL    = %s
DOMAIN      = localhost
DISABLE_SSH = true

[packages]
ENABLED = true

[log]
ROOT_PATH = %s

[security]
INSTALL_LOCK = true
SECRET_KEY   = AUTO
`, p.RunUser, p.WorkPath, p.DBPath, p.RepoRoot, p.Port, p.RootURL, p.LogPath))
}

func writeINI(iniPath, content string) (bool, error) {
	if err := os.MkdirAll(filepath.Dir(iniPath), 0o750); err != nil {
		return false, fmt.Errorf("mkdir %s: %w", filepath.Dir(iniPath), err)
	}
	if err := os.WriteFile(iniPath, []byte(content), 0o640); err != nil {
		return false, fmt.Errorf("write %s: %w", iniPath, err)
	}
	return true, nil
}
