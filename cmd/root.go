package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "forgejo-forge",
	Short: "Forgejo setup and management tool for Linux (systemd/proot) and Windows",
	Long: `forgejo-forge is a self-contained CLI for installing, configuring, and
management for Linux (systemd & proot/Termux) and Windows environments.`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
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
}
