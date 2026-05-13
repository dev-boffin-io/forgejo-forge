package cmd

import (
	"fmt"
	"os/exec"
	"strings"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/runner"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var stopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop a running Forgejo instance",
	RunE:  runStop,
}

func runStop(_ *cobra.Command, _ []string) error {
	mode := detect.Env()
	fmt.Printf("▶ Mode: %s\n", mode)
	switch mode {
	case detect.ModeSystemd:
		return stopSystemd()
	case detect.ModeWindows:
		return stopWindows()
	default:
		return stopProot()
	}
}

func stopSystemd() error {
	out, err := exec.Command("systemctl", "stop", "forgejo").CombinedOutput()
	if err != nil {
		return fmt.Errorf("systemctl stop forgejo: %w\n%s", err, strings.TrimSpace(string(out)))
	}
	fmt.Println("✔ Forgejo stopped (systemd)")
	return nil
}

func stopProot() error {
	if err := exec.Command("pkill", "-f", "forgejo web").Run(); err != nil {
		fmt.Println("⚠ No running Forgejo process found")
		return nil
	}
	fmt.Println("✔ Forgejo stopped (proot)")
	return nil
}

func stopWindows() error {
	paths, err := svc.Resolve(detect.ModeWindows)
	if err != nil {
		return err
	}
	runner.KillExisting(paths.PIDFile)
	fmt.Println("✔ Forgejo stopped (Windows)")
	return nil
}
