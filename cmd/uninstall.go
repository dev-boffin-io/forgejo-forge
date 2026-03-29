package cmd

import (
	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var uninstallCmd = &cobra.Command{
	Use:   "uninstall",
	Short: "Remove Forgejo config, data, and service files",
	RunE: func(_ *cobra.Command, _ []string) error {
		return svc.Uninstall(detect.Env())
	},
}
