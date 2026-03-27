package cmd

import (
	"github.com/dev-boffin-io/gitea-forge/internal/detect"
	"github.com/dev-boffin-io/gitea-forge/internal/svc"
	"github.com/spf13/cobra"
)

var statusPort int

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show Gitea status and access URLs",
	Run: func(_ *cobra.Command, _ []string) {
		svc.Status(detect.Env(), statusPort)
	},
}

func init() {
	statusCmd.Flags().IntVar(&statusPort, "port", 3000, "Port to check")
}
