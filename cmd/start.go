package cmd

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/dev-boffin-io/gitea-forge/internal/config"
	"github.com/dev-boffin-io/gitea-forge/internal/detect"
	"github.com/dev-boffin-io/gitea-forge/internal/netutil"
	"github.com/dev-boffin-io/gitea-forge/internal/runner"
	"github.com/dev-boffin-io/gitea-forge/internal/svc"
	"github.com/spf13/cobra"
)

var startCmd = &cobra.Command{
	Use:   "start",
	Short: "Start a previously configured Gitea instance",
	RunE:  runStart,
}

func runStart(_ *cobra.Command, _ []string) error {
	mode := detect.Env()
	fmt.Printf("▶ Mode: %s\n", mode)

	giteaBin := detect.GiteaBin()
	if giteaBin == "" {
		return fmt.Errorf("❌ gitea not found in PATH")
	}

	paths, err := svc.Resolve(mode)
	if err != nil {
		return err
	}

	// Guard: config must exist before attempting start.
	if err := config.Exists(paths.IniPath); err != nil {
		return err
	}

	// Read port directly from app.ini — no manual --port needed.
	port := config.ReadPort(paths.IniPath, 3000)

	switch mode {
	case detect.ModeSystemd:
		out, err := exec.Command("systemctl", "start", "gitea").CombinedOutput()
		if err != nil {
			return fmt.Errorf("systemctl start gitea: %w\n%s", err, out)
		}
		fmt.Println("✔ Gitea started (systemd)")

	default:
		runner.KillExisting()
		pid, err := runner.StartBackground(giteaBin, paths.IniPath, paths.LogFile, paths.BaseDir)
		if err != nil {
			return err
		}
		fmt.Printf("✔ Gitea started (PID %d)\n", pid)
	}

	if err := netutil.WaitForPort(port, 30); err != nil {
		// Show last log lines to help diagnose the crash.
		fmt.Fprintln(os.Stderr, "\n📄 Last log lines:")
		_ = exec.Command("tail", "-n", "20", paths.LogFile).Run()
		return err
	}

	netutil.PrintAccessURLs(port)
	return nil
}
