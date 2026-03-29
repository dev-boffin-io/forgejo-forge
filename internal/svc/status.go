package svc

import (
	"fmt"
	"os/exec"
	"strings"

	"github.com/dev-boffin-io/forgejo-forge/internal/config"
	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/netutil"
)

// Status prints the current Forgejo service status and access URLs.
// Port is read directly from app.ini — no need to pass it manually.
func Status(mode detect.Mode, _ int) {
	fmt.Printf("▶ Mode: %s\n", mode)

	paths, err := Resolve(mode)
	if err != nil {
		fmt.Println("● Forgejo: unknown (cannot resolve paths)")
		return
	}

	port := config.ReadPort(paths.IniPath, 3000)

	switch mode {
	case detect.ModeSystemd:
		statusSystemd(port)
	default:
		statusProot(port)
	}
}

func statusSystemd(port int) {
	out, err := exec.Command("systemctl", "is-active", "forgejo").Output()
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
