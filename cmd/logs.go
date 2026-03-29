package cmd

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var logsFollow bool
var logsLines int

var logsCmd = &cobra.Command{
	Use:   "logs",
	Short: "Show or follow Gitea logs",
	RunE:  runLogs,
}

func init() {
	logsCmd.Flags().BoolVarP(&logsFollow, "follow", "f", true, "Follow log output")
	logsCmd.Flags().IntVarP(&logsLines, "lines", "n", 50, "Number of lines to show")
}

func runLogs(_ *cobra.Command, _ []string) error {
	mode := detect.Env()

	switch mode {
	case detect.ModeSystemd:
		return logsSystemd()
	default:
		return logsProot()
	}
}

func logsSystemd() error {
	args := []string{"-u", "gitea", "--no-pager", "-n", fmt.Sprintf("%d", logsLines)}
	if logsFollow {
		args = append(args, "-f")
	}
	cmd := exec.Command("journalctl", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func logsProot() error {
	paths, err := svc.Resolve(detect.ModeProot)
	if err != nil {
		return err
	}

	if _, err := os.Stat(paths.LogFile); os.IsNotExist(err) {
		return fmt.Errorf("log file not found: %s", paths.LogFile)
	}

	args := []string{fmt.Sprintf("-n%d", logsLines)}
	if logsFollow {
		args = append(args, "-f")
	}
	args = append(args, paths.LogFile)

	cmd := exec.Command("tail", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
