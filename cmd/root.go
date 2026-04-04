package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "forgejo-forge",
	Short: "Forgejo setup and management tool for systemd and proot environments",
	Long: `forgejo-forge automates Forgejo installation, configuration, and lifecycle
management for both production (systemd) and proot/Termux environments.

Commands:
  setup        Install and configure Forgejo
  start        Start a configured Forgejo instance
  stop         Stop a running Forgejo instance
  restart      Restart Forgejo
  status       Show Forgejo status and access URLs
  logs         Follow Forgejo logs
  email-setup  Configure SMTP mailer in app.ini
  uninstall    Remove Forgejo config, data, and service files`,
}

func Execute() {
	rootCmd.AddCommand(
		setupCmd,
		startCmd,
		stopCmd,
		restartCmd,
		statusCmd,
		logsCmd,
		emailCmd,
		uninstallCmd,
	)

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
