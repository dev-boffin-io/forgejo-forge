package svc

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
)

// Uninstall removes Forgejo configuration, data, and service files.
// Prompts the user for confirmation before removing data.
func Uninstall(mode detect.Mode) error {
	paths, err := Resolve(mode)
	if err != nil {
		return err
	}

	fmt.Println("⚠  This will remove Forgejo config, data, and service files.")
	if !confirm("Continue? [y/N]: ") {
		fmt.Println("Aborted.")
		return nil
	}

	switch mode {
	case detect.ModeSystemd:
		return uninstallSystemd(paths)
	case detect.ModeWindows:
		return uninstallWindows(paths)
	default:
		return uninstallProot(paths)
	}
}

func uninstallSystemd(paths Paths) error {
	for _, args := range [][]string{
		{"stop", "forgejo"},
		{"disable", "forgejo"},
	} {
		out, err := exec.Command("systemctl", args...).CombinedOutput()
		if err != nil {
			fmt.Printf("⚠ systemctl %v: %s\n", args, strings.TrimSpace(string(out)))
		}
	}

	unitFile := "/etc/systemd/system/forgejo.service"
	if err := os.Remove(unitFile); err != nil && !os.IsNotExist(err) {
		fmt.Printf("⚠ remove %s: %v\n", unitFile, err)
	} else {
		fmt.Printf("✔ Removed: %s\n", unitFile)
	}

	_ = exec.Command("systemctl", "daemon-reload").Run()
	removeDir("/etc/forgejo")
	removeDir("/var/lib/forgejo")
	fmt.Println("✔ Forgejo uninstalled (systemd)")
	return nil
}

func uninstallProot(paths Paths) error {
	_ = exec.Command("pkill", "-f", "forgejo web").Run()
	removeDir(paths.BaseDir)
	fmt.Println("✔ Forgejo uninstalled (proot)")
	return nil
}

func uninstallWindows(paths Paths) error {
	if runtime.GOOS == "windows" {
		// Try PID file first for clean shutdown
		if paths.PIDFile != "" {
			data, err := os.ReadFile(paths.PIDFile)
			if err == nil {
				pidStr := strings.TrimSpace(string(data))
				_ = exec.Command("taskkill", "/F", "/PID", pidStr).Run()
				_ = os.Remove(paths.PIDFile)
			}
		}
		_ = exec.Command("taskkill", "/F", "/IM", "gitea.exe").Run()
	} else {
		_ = exec.Command("pkill", "-f", "forgejo web").Run()
	}
	removeDir(paths.BaseDir)
	fmt.Println("✔ Forgejo uninstalled (Windows)")
	return nil
}

func removeDir(path string) {
	if err := os.RemoveAll(path); err != nil {
		fmt.Printf("⚠ remove %s: %v\n", path, err)
	} else {
		fmt.Printf("✔ Removed: %s\n", path)
	}
}

func confirm(prompt string) bool {
	fmt.Print(prompt)
	sc := bufio.NewScanner(os.Stdin)
	if sc.Scan() {
		return strings.ToLower(strings.TrimSpace(sc.Text())) == "y"
	}
	return false
}
