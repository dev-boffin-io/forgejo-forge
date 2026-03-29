package cmd

import (
	"fmt"
	"os/exec"
	"strings"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
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
	default:
		return stopProot()
	}
}

func stopSystemd() error {
	out, err := exec.Command("systemctl", "stop", "gitea").CombinedOutput()
	if err != nil {
		return fmt.Errorf("systemctl stop gitea: %w\n%s", err, strings.TrimSpace(string(out)))
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
