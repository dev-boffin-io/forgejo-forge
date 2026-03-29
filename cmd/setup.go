package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"

	"github.com/dev-boffin-io/forgejo-forge/internal/admin"
	"github.com/dev-boffin-io/forgejo-forge/internal/config"
	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/netutil"
	"github.com/dev-boffin-io/forgejo-forge/internal/runner"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var (
	flagUsername string
	flagPassword string
	flagEmail    string
	flagPort     int
	flagDomain   string
)

var setupCmd = &cobra.Command{
	Use:   "setup",
	Short: "Install and configure Forgejo (auto-detects systemd or proot)",
	RunE:  runSetup,
}

func init() {
	setupCmd.Flags().StringVar(&flagUsername, "username", "admin", "Admin username")
	setupCmd.Flags().StringVar(&flagPassword, "password", "", "Admin password (required)")
	setupCmd.Flags().StringVar(&flagEmail, "email", "", "Admin email (defaults to <username>@example.com)")
	setupCmd.Flags().IntVar(&flagPort, "port", 3000, "Preferred HTTP port (auto-increments if busy)")
	setupCmd.Flags().StringVar(&flagDomain, "domain", "", "Custom domain for ROOT_URL (e.g. git.local)")

	_ = setupCmd.MarkFlagRequired("password")
}

func runSetup(cmd *cobra.Command, _ []string) error {
	if flagEmail == "" {
		flagEmail = admin.DefaultEmail(flagUsername)
	}

	giteaBin := detect.ForgejoBin()
	if giteaBin == "" {
		return fmt.Errorf("❌ gitea not found in PATH")
	}
	fmt.Printf("✔ Using binary: %s\n", giteaBin)

	mode := detect.Env()
	fmt.Printf("▶ Detected mode: %s\n", mode)

	// Auto port detection
	port, err := netutil.FindFreePort(flagPort)
	if err != nil {
		return fmt.Errorf("port detection: %w", err)
	}
	if port != flagPort {
		fmt.Printf("⚠ Port %d busy → using %d\n", flagPort, port)
	}
	flagPort = port

	switch mode {
	case detect.ModeSystemd:
		return setupSystemd(giteaBin)
	default:
		return setupProot(giteaBin)
	}
}

// ── Systemd ──────────────────────────────────────────────────────────────────

func setupSystemd(giteaBin string) error {
	if os.Geteuid() != 0 {
		return fmt.Errorf("❌ systemd mode requires root (sudo forgejo-forge setup ...)")
	}

	const (
		giteaUser = "git"
		giteaHome = "/var/lib/forgejo"
		giteaConf = "/etc/forgejo"
	)

	paths, _ := svc.Resolve(detect.ModeSystemd)

	fmt.Println("▶ Setting up production (systemd)...")

	if err := ensureSystemUser(giteaUser, giteaHome); err != nil {
		return err
	}

	dirs := []string{
		filepath.Join(giteaHome, "data", "log"),
		filepath.Join(giteaHome, "data", "lfs"),
		filepath.Join(giteaHome, "repositories"),
		giteaConf,
	}
	if err := mkdirs(dirs, 0o750); err != nil {
		return err
	}
	if err := chownR(giteaHome, giteaUser); err != nil {
		return err
	}

	rootURL := buildRootURL(flagDomain, flagPort)

	written, err := config.WriteSystemd(paths.IniPath, config.SystemdParams{
		RunUser:  giteaUser,
		WorkPath: giteaHome,
		DBPath:   filepath.Join(giteaHome, "data", "forgejo.db"),
		RepoRoot: filepath.Join(giteaHome, "repositories"),
		Port:     flagPort,
		RootURL:  rootURL,
		LogPath:  filepath.Join(giteaHome, "data", "log"),
	})
	if err != nil {
		return err
	}
	if written {
		if err := chown(paths.IniPath, giteaUser); err != nil {
			return err
		}
		fmt.Printf("✔ Config written: %s\n", paths.IniPath)
	} else {
		fmt.Printf("⚠ Config already exists, skipping overwrite: %s\n", paths.IniPath)
	}

	if err := writeSystemdUnit(giteaBin, paths.IniPath); err != nil {
		return err
	}

	for _, args := range [][]string{
		{"daemon-reload"},
		{"enable", "gitea"},
		{"restart", "gitea"},
	} {
		if out, err := exec.Command("systemctl", args...).CombinedOutput(); err != nil {
			return fmt.Errorf("systemctl %v: %w\n%s", args, err, out)
		}
	}

	if err := netutil.WaitForPort(flagPort, 30); err != nil {
		return err
	}
	if err := admin.CreateUser(admin.CreateOptions{
		ForgejoBin: giteaBin,
		IniPath:  paths.IniPath,
		WorkDir:  "/var/lib/forgejo",
		Username: flagUsername,
		Password: flagPassword,
		Email:    flagEmail,
	}); err != nil {
		return err
	}

	printSummary("systemd", flagPort, flagUsername, flagPassword, "")
	return nil
}

func writeSystemdUnit(giteaBin, iniPath string) error {
	const unitPath = "/etc/systemd/system/forgejo.service"
	content := fmt.Sprintf(`[Unit]
Description=Forgejo
After=network.target

[Service]
User=git
ExecStart=%s web --config %s
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
`, giteaBin, iniPath)

	if err := os.WriteFile(unitPath, []byte(content), 0o644); err != nil {
		return fmt.Errorf("write systemd unit: %w", err)
	}
	fmt.Printf("✔ Systemd unit written: %s\n", unitPath)
	return nil
}

// ── Proot ────────────────────────────────────────────────────────────────────

func setupProot(giteaBin string) error {
	currentUser, err := user.Current()
	if err != nil {
		return fmt.Errorf("get current user: %w", err)
	}

	paths, err := svc.Resolve(detect.ModeProot)
	if err != nil {
		return err
	}

	fmt.Println("▶ Setting up Proot mode...")

	dirs := []string{
		filepath.Join(paths.BaseDir, "data", "log"),
		filepath.Join(paths.BaseDir, "data", "lfs"),
		filepath.Join(paths.BaseDir, "repositories"),
		filepath.Dir(paths.IniPath),
	}
	if err := mkdirs(dirs, 0o750); err != nil {
		return err
	}

	rootURL := buildRootURL(flagDomain, flagPort)

	written, err := config.WriteProot(paths.IniPath, config.ProotParams{
		RunUser:  currentUser.Username,
		WorkPath: paths.BaseDir,
		DBPath:   filepath.Join(paths.BaseDir, "data", "forgejo.db"),
		RepoRoot: filepath.Join(paths.BaseDir, "repositories"),
		Port:     flagPort,
		RootURL:  rootURL,
		LogPath:  filepath.Join(paths.BaseDir, "data", "log"),
	})
	if err != nil {
		return err
	}
	if written {
		fmt.Printf("✔ Config written: %s\n", paths.IniPath)
	} else {
		fmt.Printf("⚠ Config already exists, skipping overwrite: %s\n", paths.IniPath)
	}

	runner.KillExisting()

	pid, err := runner.StartBackground(giteaBin, paths.IniPath, paths.LogFile, paths.BaseDir)
	if err != nil {
		return err
	}
	fmt.Printf("✔ Forgejo started (PID %d)\n", pid)

	if err := netutil.WaitForPort(flagPort, 30); err != nil {
		return err
	}
	if err := admin.CreateUser(admin.CreateOptions{
		ForgejoBin: giteaBin,
		IniPath:  paths.IniPath,
		WorkDir:  paths.BaseDir,
		Username: flagUsername,
		Password: flagPassword,
		Email:    flagEmail,
	}); err != nil {
		return err
	}

	printSummary("proot", flagPort, flagUsername, flagPassword, paths.LogFile)
	return nil
}

// ── Helpers ───────────────────────────────────────────────────────────────────

func buildRootURL(domain string, port int) string {
	if domain != "" {
		return fmt.Sprintf("http://%s/", domain)
	}
	return fmt.Sprintf("http://localhost:%d/", port)
}

func printSummary(mode string, port int, username, password, logFile string) {
	fmt.Printf("\n🚀 Forgejo running (%s mode)\n", mode)
	netutil.PrintAccessURLs(port)
	fmt.Printf("👤 %s / %s\n", username, password)
	if logFile != "" {
		fmt.Printf("📄 Log:  %s\n", logFile)
	}
	if mode == "systemd" {
		fmt.Println("🛑 Stop: sudo forgejo-forge stop")
	} else {
		fmt.Println("🛑 Stop: forgejo-forge stop")
	}
}

func mkdirs(paths []string, perm os.FileMode) error {
	for _, p := range paths {
		if err := os.MkdirAll(p, perm); err != nil {
			return fmt.Errorf("mkdir %s: %w", p, err)
		}
	}
	return nil
}

func chownR(path, username string) error {
	out, err := exec.Command("chown", "-R", username+":"+username, path).CombinedOutput()
	if err != nil {
		return fmt.Errorf("chown -R %s: %w\n%s", path, err, out)
	}
	return nil
}

func chown(path, username string) error {
	out, err := exec.Command("chown", username+":"+username, path).CombinedOutput()
	if err != nil {
		return fmt.Errorf("chown %s: %w\n%s", path, err, out)
	}
	return nil
}

func ensureSystemUser(username, homeDir string) error {
	if _, err := user.Lookup(username); err == nil {
		fmt.Printf("✔ System user %q already exists\n", username)
		return nil
	}
	out, err := exec.Command("useradd",
		"--system", "-m", "-d", homeDir, "-s", "/bin/bash", username,
	).CombinedOutput()
	if err != nil {
		return fmt.Errorf("useradd %s: %w\n%s", username, err, out)
	}
	fmt.Printf("✔ Created system user %q\n", username)
	return nil
}
