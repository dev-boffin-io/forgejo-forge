package svc

import (
	"fmt"
	"os/exec"
	"strings"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/netutil"
)

// Status prints the current Gitea service status and access URLs.
func Status(mode detect.Mode, port int) {
	fmt.Printf("▶ Mode: %s\n", mode)

	switch mode {
	case detect.ModeSystemd:
		statusSystemd(port)
	default:
		statusProot(port)
	}
}

func statusSystemd(port int) {
	out, err := exec.Command("systemctl", "is-active", "gitea").Output()
	state := strings.TrimSpace(string(out))
	if err != nil || state != "active" {
		fmt.Printf("● Forgejo: %s\n", state)
		return
	}
	fmt.Println("● Forgejo: active (running)")
	netutil.PrintAccessURLs(port)
}

func statusProot(port int) {
	if !netutil.IsPortFree(port) {
		fmt.Printf("● Forgejo: running (port %d)\n", port)
		netutil.PrintAccessURLs(port)
	} else {
		fmt.Printf("● Forgejo: stopped (port %d is free)\n", port)
	}
}
