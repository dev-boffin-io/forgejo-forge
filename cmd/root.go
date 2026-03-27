package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "gitea-forge",
	Short: "Gitea setup and management tool for systemd and proot environments",
	Long: `gitea-forge automates Gitea installation, configuration, and lifecycle
management for both production (systemd) and proot/Termux environments.

Commands:
  setup      Install and configure Gitea
  start      Start a configured Gitea instance
  stop       Stop a running Gitea instance
  restart    Restart Gitea
  status     Show Gitea status and access URLs
  logs       Follow Gitea logs
  uninstall  Remove Gitea config, data, and service files`,
}

func Execute() {
	rootCmd.AddCommand(
		setupCmd,
		startCmd,
		stopCmd,
		restartCmd,
		statusCmd,
		logsCmd,
		uninstallCmd,
	)

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
