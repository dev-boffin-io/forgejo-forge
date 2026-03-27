package svc

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/dev-boffin-io/gitea-forge/internal/detect"
)

// Uninstall removes Gitea configuration, data, and service files.
// Prompts the user for confirmation before removing data.
func Uninstall(mode detect.Mode) error {
	paths, err := Resolve(mode)
	if err != nil {
		return err
	}

	fmt.Println("⚠  This will remove Gitea config, data, and service files.")
	if !confirm("Continue? [y/N]: ") {
		fmt.Println("Aborted.")
		return nil
	}

	switch mode {
	case detect.ModeSystemd:
		return uninstallSystemd(paths)
	default:
		return uninstallProot(paths)
	}
}

func uninstallSystemd(paths Paths) error {
	// Stop and disable service
	for _, args := range [][]string{
		{"stop", "gitea"},
		{"disable", "gitea"},
	} {
		out, err := exec.Command("systemctl", args...).CombinedOutput()
		if err != nil {
			fmt.Printf("⚠ systemctl %v: %s\n", args, strings.TrimSpace(string(out)))
		}
	}

	// Remove unit file
	unitFile := "/etc/systemd/system/gitea.service"
	if err := os.Remove(unitFile); err != nil && !os.IsNotExist(err) {
		fmt.Printf("⚠ remove %s: %v\n", unitFile, err)
	} else {
		fmt.Printf("✔ Removed: %s\n", unitFile)
	}

	// Reload daemon
	_ = exec.Command("systemctl", "daemon-reload").Run()

	// Remove config dir
	removeDir("/etc/gitea")

	// Remove data dir
	removeDir("/var/lib/gitea")

	fmt.Println("✔ Gitea uninstalled (systemd)")
	return nil
}

func uninstallProot(paths Paths) error {
	// Kill process
	_ = exec.Command("pkill", "-f", "gitea web").Run()

	// Remove data tree
	removeDir(paths.BaseDir)

	fmt.Println("✔ Gitea uninstalled (proot)")
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
