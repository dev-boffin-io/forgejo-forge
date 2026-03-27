package config

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// ReadPort reads HTTP_PORT from an app.ini file.
// Returns defaultPort if the key is not found or the file cannot be read.
func ReadPort(iniPath string, defaultPort int) int {
	f, err := os.Open(iniPath)
	if err != nil {
		return defaultPort
	}
	defer f.Close()

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if strings.HasPrefix(line, "HTTP_PORT") {
			parts := strings.SplitN(line, "=", 2)
			if len(parts) == 2 {
				if p, err := strconv.Atoi(strings.TrimSpace(parts[1])); err == nil {
					return p
				}
			}
		}
	}
	return defaultPort
}

// Exists returns nil when iniPath is present, or a descriptive error.
func Exists(iniPath string) error {
	if _, err := os.Stat(iniPath); os.IsNotExist(err) {
		return fmt.Errorf("config not found: %s\n  → run 'gitea-forge setup' first", iniPath)
	}
	return nil
}
