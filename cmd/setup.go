package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"runtime"

	"github.com/dev-boffin-io/forgejo-forge/internal/admin"
	"github.com/dev-boffin-io/forgejo-forge/internal/config"
	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/netutil"
	"github.com/dev-boffin-io/forgejo-forge/internal/runner"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var (
	flagUsername   string
	flagPassword   string
	flagEmail      string
	flagPort       int
	flagDomain     string
	flagActions    bool
	flagPushCreate bool
)

var setupCmd = &cobra.Command{
	Use:   "setup",
	Short: "Install and configure Forgejo (auto-detects systemd, proot, or Windows)",
	RunE:  runSetup,
}

func init() {
	setupCmd.Flags().StringVar(&flagUsername, "username", "admin", "Admin username")
	setupCmd.Flags().StringVar(&flagPassword, "password", "", "Admin password (required)")
	setupCmd.Flags().StringVar(&flagEmail, "email", "", "Admin email (defaults to <username>@example.com)")
	setupCmd.Flags().IntVar(&flagPort, "port", 3000, "Preferred HTTP port (auto-increments if busy)")
	setupCmd.Flags().StringVar(&flagDomain, "domain", "", "Custom domain for ROOT_URL (e.g. git.local)")
	setupCmd.Flags().BoolVar(&flagActions, "actions", true, "Enable Forgejo Actions (CI/CD) and local artifact storage in app.ini (default: true; disable with --actions=false)")
	setupCmd.Flags().BoolVar(&flagPushCreate, "push-create", true, "Enable push-to-create (auto-create repos on first push)")

	_ = setupCmd.MarkFlagRequired("password")
}

func runSetup(cmd *cobra.Command, _ []string) error {
	if flagEmail == "" {
		flagEmail = admin.DefaultEmail(flagUsername)
	}

	forgejoBin := detect.ForgejoBin()
	if forgejoBin == "" {
		return fmt.Errorf("❌ forge binary not found in PATH — run: forgejo-main install")
	}
	fmt.Printf("✔ Using binary: %s\n", forgejoBin)

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
		return setupSystemd(forgejoBin)
	case detect.ModeWindows:
		return setupWindows(forgejoBin)
	default:
		return setupProot(forgejoBin)
	}
}

// applyActionsConfig enables Forgejo Actions (CI/CD) and local artifact
// storage in app.ini when --actions is set. Safe to call even if the
// sections already exist — existing keys are updated in place.
//
// baseDir is the per-mode data directory (paths.BaseDir for proot/windows;
// pass "" for systemd, which falls back to /var/lib/forgejo). The artifact
// cache is stored at <baseDir>/artifacts.
func applyActionsConfig(iniPath, baseDir string) error {
	if !flagActions {
		return nil
	}
	return enableActionsConfig(iniPath, baseDir)
}

// applyPushCreateConfig enables push-to-create (auto-create repo on first push)
// in app.ini when --push-create is set (default: true). Safe to call even if
// the [repository] section already exists — existing keys are updated in place.
func applyPushCreateConfig(iniPath string) error {
	if !flagPushCreate {
		return nil
	}
	return enablePushCreateConfig(iniPath)
}

// enablePushCreateConfig does the actual work of writing ENABLE_PUSH_CREATE_USER
// and ENABLE_PUSH_CREATE_ORG into [repository] in app.ini. Shared by
// `setup --push-create` and `config enable-push-create`.
func enablePushCreateConfig(iniPath string) error {
	if err := config.SetKey(iniPath, "repository", "ENABLE_PUSH_CREATE_USER", "true"); err != nil {
		return fmt.Errorf("enable push-to-create (user): %w", err)
	}
	if err := config.SetKey(iniPath, "repository", "ENABLE_PUSH_CREATE_ORG", "true"); err != nil {
		return fmt.Errorf("enable push-to-create (org): %w", err)
	}
	fmt.Println("✔ Push-to-create enabled (user repos + org repos)")
	return nil
}
// [actions.artifacts] (including a concrete PATH) into app.ini, regardless
// of any CLI flag. Shared by `setup --actions` and `config enable-actions`.
func enableActionsConfig(iniPath, baseDir string) error {
	if baseDir == "" {
		baseDir = "/var/lib/forgejo"
	}
	artifactsPath := filepath.Join(baseDir, "artifacts")
	if err := os.MkdirAll(artifactsPath, 0o750); err != nil {
		return fmt.Errorf("create artifacts dir %s: %w", artifactsPath, err)
	}

	if err := config.SetKey(iniPath, "actions", "ENABLED", "true"); err != nil {
		return fmt.Errorf("enable [actions]: %w", err)
	}
	if err := config.SetKey(iniPath, "actions.artifacts", "STORAGE_TYPE", "local"); err != nil {
		return fmt.Errorf("enable [actions.artifacts]: %w", err)
	}
	if err := config.SetKey(iniPath, "actions.artifacts", "PATH", artifactsPath); err != nil {
		return fmt.Errorf("set [actions.artifacts] PATH: %w", err)
	}
	fmt.Printf("✔ Forgejo Actions + local artifact storage enabled (cache: %s)\n", artifactsPath)
	return nil
}

// ── Systemd ───────────────────────────────────────────────────────────────────

func setupSystemd(forgejoBin string) error {
	if os.Geteuid() != 0 {
		return fmt.Errorf("❌ systemd mode requires root (sudo forgejo-forge setup ...)")
	}

	const (
		forgejoUser = "git"
		forgejoHome = "/var/lib/forgejo"
		forgejoConf = "/etc/forgejo"
	)

	paths, _ := svc.Resolve(detect.ModeSystemd)

	fmt.Println("▶ Setting up production (systemd)...")

	if err := ensureSystemUser(forgejoUser, forgejoHome); err != nil {
		return err
	}

	dirs := []string{
		filepath.Join(forgejoHome, "data", "log"),
		filepath.Join(forgejoHome, "data", "lfs"),
		filepath.Join(forgejoHome, "repositories"),
		forgejoConf,
	}
	if err := mkdirs(dirs, 0o750); err != nil {
		return err
	}
	if err := chownR(forgejoHome, forgejoUser); err != nil {
		return err
	}

	rootURL := buildRootURL(flagDomain, flagPort)

	written, err := config.WriteSystemd(paths.IniPath, config.SystemdParams{
		RunUser:  forgejoUser,
		WorkPath: forgejoHome,
		DBPath:   filepath.Join(forgejoHome, "data", "forgejo.db"),
		RepoRoot: filepath.Join(forgejoHome, "repositories"),
		Port:     flagPort,
		RootURL:  rootURL,
		LogPath:  filepath.Join(forgejoHome, "data", "log"),
	})
	if err != nil {
		return err
	}
	if written {
		if err := chown(paths.IniPath, forgejoUser); err != nil {
			return err
		}
		fmt.Printf("✔ Config written: %s\n", paths.IniPath)
	} else {
		fmt.Printf("⚠ Config already exists, skipping overwrite: %s\n", paths.IniPath)
	}

	if err := applyActionsConfig(paths.IniPath, paths.BaseDir); err != nil {
		return err
	}

	if err := applyPushCreateConfig(paths.IniPath); err != nil {
		return err
	}

	if err := writeSystemdUnit(forgejoBin, paths.IniPath); err != nil {
		return err
	}

	for _, args := range [][]string{
		{"daemon-reload"},
		{"enable", "forgejo"},
		{"restart", "forgejo"},
	} {
		if out, err := exec.Command("systemctl", args...).CombinedOutput(); err != nil {
			return fmt.Errorf("systemctl %v: %w\n%s", args, err, out)
		}
	}

	if err := netutil.WaitForPort(flagPort, 30); err != nil {
		return err
	}
	if err := admin.CreateUser(admin.CreateOptions{
		ForgejoBin: forgejoBin,
		IniPath:    paths.IniPath,
		WorkDir:    "/var/lib/forgejo",
		Username:   flagUsername,
		Password:   flagPassword,
		Email:      flagEmail,
	}); err != nil {
		return err
	}

	printSummary("systemd", flagPort, flagUsername, flagPassword, "")
	return nil
}

func writeSystemdUnit(forgejoBin, iniPath string) error {
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
`, forgejoBin, iniPath)

	if err := os.WriteFile(unitPath, []byte(content), 0o644); err != nil {
		return fmt.Errorf("write systemd unit: %w", err)
	}
	fmt.Printf("✔ Systemd unit written: %s\n", unitPath)
	return nil
}

// ── Proot ─────────────────────────────────────────────────────────────────────

func setupProot(forgejoBin string) error {
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

	if err := applyActionsConfig(paths.IniPath, paths.BaseDir); err != nil {
		return err
	}

	if err := applyPushCreateConfig(paths.IniPath); err != nil {
		return err
	}

	runner.KillExisting()
	pid, err := runner.StartBackground(forgejoBin, paths.IniPath, paths.LogFile, paths.BaseDir)
	if err != nil {
		return err
	}
	fmt.Printf("✔ Forgejo started (PID %d)\n", pid)

	if err := netutil.WaitForPort(flagPort, 30); err != nil {
		return err
	}
	if err := admin.CreateUser(admin.CreateOptions{
		ForgejoBin: forgejoBin,
		IniPath:    paths.IniPath,
		WorkDir:    paths.BaseDir,
		Username:   flagUsername,
		Password:   flagPassword,
		Email:      flagEmail,
	}); err != nil {
		return err
	}

	printSummary("proot", flagPort, flagUsername, flagPassword, paths.LogFile)
	return nil
}

// ── Windows ───────────────────────────────────────────────────────────────────

func setupWindows(forgejoBin string) error {
	_ = runtime.GOOS

	paths, err := svc.Resolve(detect.ModeWindows)
	if err != nil {
		return err
	}

	fmt.Println("▶ Setting up Windows mode...")
	fmt.Printf("   Data directory: %s\n", paths.BaseDir)

	currentUser, err := user.Current()
	if err != nil {
		return fmt.Errorf("get current user: %w", err)
	}

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

	if err := applyActionsConfig(paths.IniPath, paths.BaseDir); err != nil {
		return err
	}

	if err := applyPushCreateConfig(paths.IniPath); err != nil {
		return err
	}

	// Kill any existing process before starting fresh
	runner.KillExisting(paths.PIDFile)

	pid, err := runner.StartBackground(forgejoBin, paths.IniPath, paths.LogFile, paths.BaseDir, paths.PIDFile)
	if err != nil {
		return err
	}
	fmt.Printf("✔ Forgejo started (PID %d)\n", pid)

	if err := netutil.WaitForPort(flagPort, 30); err != nil {
		return err
	}
	if err := admin.CreateUser(admin.CreateOptions{
		ForgejoBin: forgejoBin,
		IniPath:    paths.IniPath,
		WorkDir:    paths.BaseDir,
		Username:   flagUsername,
		Password:   flagPassword,
		Email:      flagEmail,
	}); err != nil {
		return err
	}

	printSummary("windows", flagPort, flagUsername, flagPassword, paths.LogFile)
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
	switch mode {
	case "systemd":
		fmt.Println("🛑 Stop: sudo forgejo-forge stop")
	case "windows":
		fmt.Println("🛑 Stop: forgejo-forge stop")
		fmt.Println("💡 Tip:  Add forgejo-forge to startup via Task Scheduler for auto-start")
	default:
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

// chownR and chown are Linux-only helpers; they are no-ops on Windows.
func chownR(path, username string) error {
	if runtime.GOOS == "windows" {
		return nil
	}
	out, err := exec.Command("chown", "-R", username+":"+username, path).CombinedOutput()
	if err != nil {
		return fmt.Errorf("chown -R %s: %w\n%s", path, err, out)
	}
	return nil
}

func chown(path, username string) error {
	if runtime.GOOS == "windows" {
		return nil
	}
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
