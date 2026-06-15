package cmd

import (
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"

	"github.com/spf13/cobra"
)

// ── Flags ─────────────────────────────────────────────────────────────────────

var (
	flagRunnerURL      string
	flagRunnerToken    string
	flagRunnerName     string
	flagRunnerLabels   string
	flagRunnerUUID     string
	flagRunnerClean    bool
	flagRunnerInstDir  string
	flagRunnerNoReg    bool
	flagRunnerBin      string   // explicit runner binary path override
)

// ── Command tree ──────────────────────────────────────────────────────────────

var runnerCmd = &cobra.Command{
	Use:   "runner",
	Short: "Manage forgejo-runner / act_runner (install, register, start, stop, status)",
}

var runnerInstallCmd = &cobra.Command{
	Use:   "install",
	Short: "Download and install forgejo-runner (Linux) or gitea-runner (Windows/macOS)",
	RunE:  runRunnerInstall,
}

var runnerRegisterCmd = &cobra.Command{
	Use:   "register",
	Short: "Register the runner against a Forgejo / Gitea instance",
	RunE:  runRunnerRegister,
}

var runnerStartCmd = &cobra.Command{
	Use:   "start",
	Short: "Start the runner (daemon or foreground)",
	RunE:  runRunnerStart,
}

var runnerStopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop the running runner process",
	RunE:  runRunnerStop,
}

var runnerStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show whether the runner is running",
	RunE:  runRunnerStatus,
}

var runnerUninstallCmd = &cobra.Command{
	Use:   "uninstall",
	Short: "Remove the runner binary and its config",
	RunE:  runRunnerUninstall,
}

func init() {
	// persistent flag available to all sub-commands
	runnerCmd.PersistentFlags().StringVar(&flagRunnerBin, "runner-bin", "", "Path to runner binary (overrides auto-detect)")

	// install flags
	runnerInstallCmd.Flags().StringVar(&flagRunnerInstDir, "install-dir", runnerDefaultInstDir(), "Directory to install the runner binary")

	// register flags
	runnerRegisterCmd.Flags().StringVar(&flagRunnerURL, "url", "", "Forgejo/Gitea instance URL  (required)")
	runnerRegisterCmd.Flags().StringVar(&flagRunnerToken, "token", "", "Runner registration token  (required)")
	runnerRegisterCmd.Flags().StringVar(&flagRunnerName, "name", defaultRunnerName(), "Runner name (defaults to hostname)")
	runnerRegisterCmd.Flags().StringVar(&flagRunnerLabels, "labels", "ubuntu-latest:host", "Comma-separated label list")
	runnerRegisterCmd.Flags().StringVar(&flagRunnerUUID, "uuid", "", "Runner UUID as shown on the Forgejo 'Set up runner' page (required for a clean/first-time registration; reused from config.yml if omitted)")
	runnerRegisterCmd.Flags().BoolVar(&flagRunnerClean, "clean", false, "Regenerate config.yml from scratch, discarding any previous connection/labels")
	runnerRegisterCmd.Flags().BoolVar(&flagRunnerNoReg, "no-register", false, "Skip interactive register (use existing .runner file)")
	_ = runnerRegisterCmd.MarkFlagRequired("url")
	_ = runnerRegisterCmd.MarkFlagRequired("token")

	runnerCmd.AddCommand(
		runnerInstallCmd,
		runnerRegisterCmd,
		runnerStartCmd,
		runnerStopCmd,
		runnerStatusCmd,
		runnerUninstallCmd,
	)
}

// ── Install ───────────────────────────────────────────────────────────────────

func runRunnerInstall(_ *cobra.Command, _ []string) error {
	dest := flagRunnerInstDir
	if err := os.MkdirAll(dest, 0o755); err != nil {
		return fmt.Errorf("create install dir %s: %w", dest, err)
	}

	binName := runnerBinName()
	binPath := filepath.Join(dest, binName)

	// Already installed?
	if ver, err := runnerInstalledVersion(binPath); err == nil {
		fmt.Printf("✔ Runner already installed: %s (%s)\n", binPath, ver)
	}

	url, version, err := runnerLatestURL()
	if err != nil {
		return fmt.Errorf("fetch latest runner release: %w", err)
	}
	fmt.Printf("▶ Downloading forgejo-runner / act_runner %s\n   %s\n", version, url)

	tmp, err := downloadToTemp(url)
	if err != nil {
		return fmt.Errorf("download runner: %w", err)
	}
	defer os.Remove(tmp)

	if err := os.Rename(tmp, binPath); err != nil {
		// Cross-device move fallback
		if err2 := copyFile(tmp, binPath); err2 != nil {
			return fmt.Errorf("install runner binary: %w", err2)
		}
	}
	if err := os.Chmod(binPath, 0o755); err != nil {
		return fmt.Errorf("chmod runner: %w", err)
	}

	fmt.Printf("✔ Installed: %s\n", binPath)
	fmt.Printf("  Next step: forgejo-forge runner register --url <URL> --token <TOKEN>\n")
	return nil
}

// ── Register ──────────────────────────────────────────────────────────────────

func runRunnerRegister(_ *cobra.Command, _ []string) error {
	bin, err := findRunnerBin()
	if err != nil {
		return err
	}

	configPath := runnerConfigPath()
	configDir := filepath.Dir(configPath)
	if err := os.MkdirAll(configDir, 0o755); err != nil {
		return fmt.Errorf("create config dir: %w", err)
	}

	// --clean: discard any previous config so this is a true fresh start.
	if flagRunnerClean {
		_ = os.Remove(configPath)
		_ = os.Remove(runnerStateFilePath())
		fmt.Println("▶ --clean: removed existing config.yml and .runner state file")
	}

	// 1. Generate a fresh default config.yml if one doesn't already exist
	if _, err := os.Stat(configPath); err != nil {
		fmt.Println("▶ Generating default runner config...")
		out, err := exec.Command(bin, "generate-config").Output()
		if err != nil {
			return fmt.Errorf("generate-config: %w", err)
		}
		if err := os.WriteFile(configPath, out, 0o644); err != nil {
			return fmt.Errorf("write config.yml: %w", err)
		}
	}

	// Warn early if this looks like a first-time registration without the
	// server-issued UUID — the daemon will likely fail with "unauthenticated:
	// unregistered runner" in that case.
	if flagRunnerUUID == "" {
		existing, _ := os.ReadFile(configPath)
		if runnerExtractUUID(string(existing)) == "" {
			fmt.Println("⚠ No --uuid given and none found in config.yml.")
			fmt.Println("  Forgejo's 'Set up runner' page shows a UUID — pass it with --uuid <uuid>")
			fmt.Println("  for a reliable first-time registration. Continuing with a random UUID...")
		}
	}

	// 2. Inject the server.connections.forgejo block (v12+ style — `register` is deprecated)
	if err := runnerInjectConnection(configPath, flagRunnerURL, flagRunnerToken, flagRunnerUUID); err != nil {
		return fmt.Errorf("update config.yml: %w", err)
	}

	// 3. Set the runner's display name
	if err := runnerSetName(configPath, flagRunnerName); err != nil {
		fmt.Printf("  ⚠ Could not set runner name in config.yml: %v\n", err)
	}

	// 4. Apply label overrides
	fmt.Printf("✔ Registered connection \"forgejo\" -> %s\n", flagRunnerURL)
	fmt.Printf("  Config: %s\n", configPath)
	fmt.Printf("  Labels: %s  (edit config.yml under runner.labels to change)\n", flagRunnerLabels)
	if err := runnerSetLabels(configPath, flagRunnerLabels); err != nil {
		fmt.Printf("  ⚠ Could not auto-set labels in config.yml: %v\n", err)
	}
	fmt.Printf("\n  Start with: forgejo-forge runner start\n")
	return nil
}

// runnerInjectConnection adds or updates the "forgejo" connection under
// server.connections in the runner's config.yml (v12+ self-registration flow).
// The connection key is always "forgejo" — this matches the key Forgejo's own
// "Set up runner" instructions use, and is independent of the runner's display name.
func runnerInjectConnection(configPath, url, token, explicitUUID string) error {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return err
	}
	text := string(data)

	if !strings.HasSuffix(url, "/") {
		url += "/"
	}

	// UUID resolution order:
	//   1. --uuid flag, if given — the value shown on Forgejo's
	//      "Set up runner" page is the source of truth.
	//   2. an existing uuid already present in config.yml (so re-running
	//      register without --uuid doesn't invalidate a working setup).
	//   3. a freshly generated random UUID, as a last resort for users who
	//      skip the Forgejo UI flow entirely.
	//
	// Re-using the same UUID matters because a registration token is
	// consumed on first successful daemon connection and becomes bound to
	// whatever UUID was used at that time. Writing a different UUID on a
	// later `register` run — while the daemon still presents the old
	// (consumed) token — causes "unauthenticated: unregistered runner".
	uuid := strings.TrimSpace(explicitUUID)
	if uuid == "" {
		uuid = runnerExtractUUID(text)
	}
	if uuid == "" {
		uuid = runnerGenUUID()
	}

	connBlock := fmt.Sprintf(
		"server:\n  connections:\n    forgejo:\n      url: %s\n      uuid: %s\n      token: %s\n",
		url, uuid, token,
	)

	if strings.Contains(text, "server:") {
		// Replace existing server: block (and everything indented under it) wholesale.
		lines := strings.Split(text, "\n")
		var out []string
		skipping := false
		for _, line := range lines {
			trimmed := strings.TrimRight(line, " \t")
			if strings.HasPrefix(trimmed, "server:") {
				skipping = true
				out = append(out, strings.TrimSuffix(connBlock, "\n"))
				continue
			}
			if skipping {
				// Still inside the old server: block if indented (or blank)
				if trimmed == "" || strings.HasPrefix(trimmed, " ") || strings.HasPrefix(trimmed, "\t") {
					continue
				}
				skipping = false
			}
			out = append(out, line)
		}
		text = strings.Join(out, "\n")
	} else {
		if !strings.HasSuffix(text, "\n") {
			text += "\n"
		}
		text += "\n" + connBlock
	}

	return os.WriteFile(configPath, []byte(text), 0o644)
}

// runnerSetLabels replaces the runner.labels list in config.yml with the
// provided comma-separated label string.
// runnerSetName replaces the runner.name field in config.yml with the
// given value, if present at the expected 2-space indent under runner:.
// If runner.name is not found, this is a no-op (the daemon falls back to
// its own default, typically the hostname).
func runnerSetName(configPath, name string) error {
	if name == "" {
		return nil
	}
	data, err := os.ReadFile(configPath)
	if err != nil {
		return err
	}
	lines := strings.Split(string(data), "\n")
	changed := false
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		indent := len(line) - len(strings.TrimLeft(line, " \t"))
		if indent == 2 && strings.HasPrefix(trimmed, "name:") {
			lines[i] = fmt.Sprintf("  name: \"%s\"", name)
			changed = true
			break
		}
	}
	if !changed {
		return nil
	}
	return os.WriteFile(configPath, []byte(strings.Join(lines, "\n")), 0o644)
}

func runnerSetLabels(configPath, labelsCSV string) error {
	if labelsCSV == "" {
		return nil
	}
	data, err := os.ReadFile(configPath)
	if err != nil {
		return err
	}
	text := string(data)
	labels := strings.Split(labelsCSV, ",")
	var sb strings.Builder
	sb.WriteString("labels:\n")
	for _, l := range labels {
		l = strings.TrimSpace(l)
		if l == "" {
			continue
		}
		sb.WriteString(fmt.Sprintf("    - \"%s\"\n", l))
	}
	newBlock := sb.String()

	lines := strings.Split(text, "\n")
	var out []string
	replaced := false
	skipping := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		indent := len(line) - len(strings.TrimLeft(line, " \t"))
		if !skipping && strings.HasPrefix(trimmed, "labels:") && indent == 2 {
			skipping = true
			replaced = true
			out = append(out, "  "+strings.TrimSuffix(newBlock, "\n"))
			continue
		}
		if skipping {
			if trimmed == "" || indent > 2 {
				continue
			}
			skipping = false
		}
		out = append(out, line)
	}
	if !replaced {
		// runner.labels not found in expected shape — skip silently, daemon
		// will use config defaults / CLI-provided labels for jobs.
		return nil
	}
	return os.WriteFile(configPath, []byte(strings.Join(out, "\n")), 0o644)
}

// ── Start ─────────────────────────────────────────────────────────────────────

func runRunnerStart(_ *cobra.Command, _ []string) error {
	bin, err := findRunnerBin()
	if err != nil {
		return err
	}

	configPath := runnerConfigPath()
	if _, err := os.Stat(configPath); err != nil {
		return fmt.Errorf("runner config not found at %s — run 'forgejo-forge runner register' first", configPath)
	}

	// Check if already running
	if pid, err := runnerPID(); err == nil {
		fmt.Printf("⚠ Runner already running (PID %d)\n", pid)
		return nil
	}

	pidFile := runnerPIDFile()
	logFile := runnerLogFile()
	if err := os.MkdirAll(filepath.Dir(logFile), 0o755); err != nil {
		return fmt.Errorf("create log dir: %w", err)
	}

	log, err := os.OpenFile(logFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return fmt.Errorf("open log file: %w", err)
	}
	defer log.Close()

	cmd := exec.Command(bin, "daemon", "--config", configPath)
	cmd.Stdout = log
	cmd.Stderr = log
	setSysProcAttr(cmd)
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start runner daemon: %w", err)
	}

	if err := os.WriteFile(pidFile, []byte(fmt.Sprintf("%d\n", cmd.Process.Pid)), 0o644); err != nil {
		return fmt.Errorf("write PID file: %w", err)
	}

	// Give the daemon time to crash on startup (bad config, bad token,
	// registration failure, etc.) before reporting success. Some failures
	// (e.g. rejected registration) surface a couple seconds in, after the
	// initial process spawn succeeds — so poll for a few seconds rather
	// than checking only once.
	const (
		checkInterval = 500 * time.Millisecond
		checkTotal    = 4 * time.Second
	)
	for waited := time.Duration(0); waited < checkTotal; waited += checkInterval {
		time.Sleep(checkInterval)
		if !runnerProcessAlive(cmd.Process.Pid) {
			_ = os.Remove(pidFile)
			fmt.Printf("✘ Runner exited shortly after starting.\n")
			fmt.Printf("  Last log lines (%s):\n", logFile)
			printTail(logFile, 30)
			return fmt.Errorf("runner daemon exited — see log above")
		}
	}

	fmt.Printf("✔ Runner started (PID %d)\n", cmd.Process.Pid)
	fmt.Printf("  Log: %s\n", logFile)
	return nil
}

// printTail prints the last n lines of a file (best-effort).
func printTail(path string, n int) {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Printf("    (could not read log: %v)\n", err)
		return
	}
	lines := strings.Split(strings.TrimRight(string(data), "\n"), "\n")
	start := 0
	if len(lines) > n {
		start = len(lines) - n
	}
	for _, l := range lines[start:] {
		fmt.Printf("    %s\n", l)
	}
}

// ── Stop ──────────────────────────────────────────────────────────────────────

func runRunnerStop(_ *cobra.Command, _ []string) error {
	pid, err := runnerPID()
	if err != nil {
		fmt.Println("⚠ Runner does not appear to be running.")
		return nil
	}
	proc, err := os.FindProcess(pid)
	if err != nil {
		return fmt.Errorf("find process %d: %w", pid, err)
	}
	if err := proc.Signal(os.Interrupt); err != nil {
		_ = proc.Kill()
	}
	_ = os.Remove(runnerPIDFile())
	fmt.Printf("✔ Runner stopped (PID %d)\n", pid)
	return nil
}

// ── Status ────────────────────────────────────────────────────────────────────

func runRunnerStatus(_ *cobra.Command, _ []string) error {
	bin, _ := findRunnerBin()
	if bin == "" {
		fmt.Println("runner binary : not installed")
	} else {
		ver, _ := runnerInstalledVersion(bin)
		fmt.Printf("runner binary : %s (%s)\n", bin, ver)
	}

	configPath := runnerConfigPath()
	if _, err := os.Stat(configPath); err == nil {
		fmt.Printf("config        : %s\n", configPath)
	} else {
		fmt.Println("config        : not found (run register first)")
	}

	pid, err := runnerPID()
	if err != nil {
		fmt.Println("status        : stopped")
		logFile := runnerLogFile()
		if _, statErr := os.Stat(logFile); statErr == nil {
			fmt.Printf("\n  Last log lines (%s):\n", logFile)
			printTail(logFile, 15)
		}
	} else {
		fmt.Printf("status        : running (PID %d)\n", pid)
	}
	return nil
}

// ── Uninstall ─────────────────────────────────────────────────────────────────

func runRunnerUninstall(_ *cobra.Command, _ []string) error {
	// Stop first if running
	if pid, err := runnerPID(); err == nil {
		proc, _ := os.FindProcess(pid)
		if proc != nil {
			_ = proc.Signal(os.Interrupt)
		}
		_ = os.Remove(runnerPIDFile())
		fmt.Printf("✔ Stopped runner (PID %d)\n", pid)
	}

	removed := 0
	for _, path := range []string{
		runnerBinPath(),
		runnerConfigPath(),
		runnerStateFilePath(),
		runnerPIDFile(),
		runnerLogFile(),
	} {
		if err := os.Remove(path); err == nil {
			fmt.Printf("  removed: %s\n", path)
			removed++
		}
	}
	if removed == 0 {
		fmt.Println("⚠ Nothing to remove — runner was not installed.")
	} else {
		fmt.Println("✔ Runner uninstalled.")
	}
	return nil
}

// ── Platform helpers ──────────────────────────────────────────────────────────

func runnerBinName() string {
	// Linux → forgejo-runner ; Windows/macOS → gitea-runner (Forgejo doesn't
	// ship binaries for those platforms; Gitea's runner is the supported
	// alternative there).
	name := "forgejo-runner"
	if runtime.GOOS == "windows" {
		name = "gitea-runner.exe"
	} else if runtime.GOOS == "darwin" {
		name = "gitea-runner"
	}
	return name
}

func runnerDefaultInstDir() string {
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "forgejo-forge", "bin")
	}
	home, _ := os.UserHomeDir()
	if os.Geteuid() == 0 {
		return "/usr/local/bin"
	}
	return filepath.Join(home, ".local", "bin")
}

func runnerBinPath() string {
	return filepath.Join(runnerDefaultInstDir(), runnerBinName())
}

func runnerConfigDir() string {
	if runtime.GOOS == "windows" {
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "forgejo-forge", "runner")
	}
	home, _ := os.UserHomeDir()
	if os.Geteuid() == 0 {
		return "/etc/forgejo-runner"
	}
	return filepath.Join(home, ".config", "forgejo-runner")
}

func runnerConfigPath() string {
	return filepath.Join(runnerConfigDir(), "config.yml")
}

func runnerStateFilePath() string {
	return filepath.Join(runnerConfigDir(), ".runner")
}

func runnerPIDFile() string {
	return filepath.Join(runnerConfigDir(), "runner.pid")
}

func runnerLogFile() string {
	return filepath.Join(runnerConfigDir(), "runner.log")
}

func defaultRunnerName() string {
	h, err := os.Hostname()
	if err != nil {
		return "my-runner"
	}
	return strings.ToLower(h)
}

// runnerGenUUID returns a random RFC-4122 v4 UUID string for use as a
// runner's connection identifier when self-registering in config.yml.
// runnerExtractUUID looks for an existing server.connections.*.uuid value
// in config.yml text. Returns "" if none is found or it's empty/placeholder.
func runnerExtractUUID(configText string) string {
	lines := strings.Split(configText, "\n")
	inServer := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		indent := len(line) - len(strings.TrimLeft(line, " \t"))
		if indent == 0 && strings.HasPrefix(trimmed, "server:") {
			inServer = true
			continue
		}
		if indent == 0 && trimmed != "" {
			inServer = false
		}
		if !inServer {
			continue
		}
		if strings.HasPrefix(trimmed, "uuid:") {
			val := strings.TrimSpace(strings.TrimPrefix(trimmed, "uuid:"))
			val = strings.Trim(val, `"'`)
			if val != "" {
				return val
			}
		}
	}
	return ""
}

func runnerGenUUID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		// Extremely unlikely; fall back to a fixed-but-valid v4 UUID.
		return "00000000-0000-4000-8000-000000000000"
	}
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// ── Binary lookup ─────────────────────────────────────────────────────────────

func findRunnerBin() (string, error) {
	// 0. Explicit --runner-bin flag
	if flagRunnerBin != "" {
		if isExec(flagRunnerBin) {
			return flagRunnerBin, nil
		}
		return "", fmt.Errorf("❌ --runner-bin path not executable: %s", flagRunnerBin)
	}
	// 1. Default install path
	if p := runnerBinPath(); isExec(p) {
		return p, nil
	}
	// 2. PATH
	for _, name := range []string{"forgejo-runner", "gitea-runner", "act_runner"} {
		if p, err := exec.LookPath(name); err == nil {
			return p, nil
		}
	}
	return "", fmt.Errorf(
		"❌ Runner binary not found. Run: forgejo-forge runner install",
	)
}

func isExec(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func runnerInstalledVersion(bin string) (string, error) {
	out, err := exec.Command(bin, "--version").CombinedOutput()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

func runnerPID() (int, error) {
	data, err := os.ReadFile(runnerPIDFile())
	if err != nil {
		return 0, err
	}
	var pid int
	if _, err := fmt.Sscanf(strings.TrimSpace(string(data)), "%d", &pid); err != nil {
		return 0, err
	}

	if runnerProcessAlive(pid) {
		return pid, nil
	}
	_ = os.Remove(runnerPIDFile())
	return 0, fmt.Errorf("process %d not running", pid)
}

// runnerProcessAlive checks whether a process with the given PID is alive.
// On Linux (including under proot/Termux, where signal-based checks via
// os.Process.Signal can be unreliable across PID namespaces), it prefers
// checking for the existence of /proc/<pid>. It falls back to a signal-0
// liveness check on other platforms.
func runnerProcessAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	if runtime.GOOS == "linux" {
		if _, err := os.Stat(fmt.Sprintf("/proc/%d", pid)); err == nil {
			return true
		}
		return false
	}
	proc, err := os.FindProcess(pid)
	if err != nil {
		return false
	}
	if runtime.GOOS == "windows" {
		// os.FindProcess on Windows opens a real handle; if the process has
		// exited, a subsequent signal will fail.
		return proc.Signal(syscall.Signal(0)) == nil
	}
	return proc.Signal(syscall.Signal(0)) == nil
}

// ── Release fetch & download ──────────────────────────────────────────────────

type ghRelease struct {
	TagName string `json:"tag_name"`
	Assets  []struct {
		Name               string `json:"name"`
		BrowserDownloadURL string `json:"browser_download_url"`
	} `json:"assets"`
}

func runnerLatestURL() (url, version string, err error) {
	if runtime.GOOS == "linux" {
		return runnerLatestForgejo()
	}
	return runnerLatestAct()
}

// runnerLatestForgejo fetches the latest forgejo-runner release.
// The runner repo lives on code.forgejo.org (not codeberg.org), with a
// read-only API mirror at data.forgejo.org. Try both, in order, each
// using the standard /releases/latest endpoint which both instances support.
func runnerLatestForgejo() (string, string, error) {
	sources := []struct {
		apiURL       string
		downloadBase string
	}{
		{"https://data.forgejo.org/api/v1/repos/forgejo/runner/releases/latest", "https://code.forgejo.org/forgejo/runner/releases/download"},
		{"https://code.forgejo.org/api/v1/repos/forgejo/runner/releases/latest", "https://code.forgejo.org/forgejo/runner/releases/download"},
	}

	suffix := runnerLinuxSuffix()
	var lastErr error

	for _, src := range sources {
		rel, err := fetchReleaseLatest(src.apiURL, "forgejo-runner")
		if err != nil {
			lastErr = err
			continue
		}
		version := strings.TrimPrefix(rel.TagName, "v")
		// Asset: forgejo-runner-<version>-linux-amd64
		assetName := fmt.Sprintf("forgejo-runner-%s-%s", version, suffix)
		for _, a := range rel.Assets {
			if a.Name == assetName {
				return a.BrowserDownloadURL, version, nil
			}
		}
		// Asset list didn't include it (or was empty) — construct direct URL
		directURL := fmt.Sprintf("%s/v%s/%s", src.downloadBase, version, assetName)
		return directURL, version, nil
	}

	return "", "", fmt.Errorf("fetch latest forgejo-runner release: %w", lastErr)
}

// runnerLatestAct fetches the latest Gitea Runner ("gitea-runner", formerly
// act_runner) release for Windows and macOS. This project lives on
// gitea.com (gitea/runner) — NOT github.com/nektos — the nektos org hosts
// the unrelated "act" CLI tool and has no act_runner releases.
// Asset naming: gitea-runner-<version>-<os>-<arch>[.exe]
//   e.g. gitea-runner-1.0.8-windows-amd64.exe, gitea-runner-1.0.8-darwin-arm64
func runnerLatestAct() (string, string, error) {
	apiURL := "https://gitea.com/api/v1/repos/gitea/runner/releases?limit=1&page=1"
	rels, err := fetchReleaseList(apiURL, "gitea-runner")
	if err != nil {
		return "", "", fmt.Errorf("fetch latest gitea-runner release: %w", err)
	}
	if len(rels) == 0 {
		return "", "", fmt.Errorf("no releases found for gitea/runner on gitea.com")
	}
	version := strings.TrimPrefix(rels[0].TagName, "v")
	needle := runnerActNeedle()
	for _, a := range rels[0].Assets {
		// Skip checksums/compressed variants — match the plain binary asset.
		if strings.HasSuffix(a.Name, ".sha256") || strings.HasSuffix(a.Name, ".xz") {
			continue
		}
		if strings.Contains(a.Name, needle) {
			return a.BrowserDownloadURL, version, nil
		}
	}
	// Fallback direct URL
	ext := ""
	if runtime.GOOS == "windows" {
		ext = ".exe"
	}
	directURL := fmt.Sprintf(
		"https://gitea.com/gitea/runner/releases/download/v%s/gitea-runner-%s-%s%s",
		version, version, needle, ext,
	)
	return directURL, version, nil
}

func runnerLinuxSuffix() string {
	switch runtime.GOARCH {
	case "arm64":
		return "linux-arm64"
	case "arm":
		return "linux-arm-6"
	default:
		return "linux-amd64"
	}
}

func runnerActNeedle() string {
	goos := runtime.GOOS
	arch := runtime.GOARCH
	ext := ""
	if goos == "windows" {
		ext = ".exe"
	}
	return fmt.Sprintf("%s-%s%s", goos, arch, ext)
}

// fetchReleaseList fetches a JSON array of releases from a Gitea/GitHub-compatible API.
func fetchReleaseList(apiURL, ua string) ([]ghRelease, error) {
	client := &http.Client{Timeout: 15 * time.Second}
	req, _ := http.NewRequest("GET", apiURL, nil)
	req.Header.Set("User-Agent", ua+"/1.0")
	req.Header.Set("Accept", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch %s: %w", apiURL, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("API returned HTTP %d for %s", resp.StatusCode, apiURL)
	}
	var rels []ghRelease
	if err := json.NewDecoder(resp.Body).Decode(&rels); err != nil {
		return nil, fmt.Errorf("decode releases JSON: %w", err)
	}
	return rels, nil
}

// fetchReleaseLatest fetches a single release object from a /releases/latest
// style endpoint (Gitea/Forgejo API), as opposed to fetchReleaseList which
// expects a JSON array from a /releases?limit=... endpoint.
func fetchReleaseLatest(apiURL, ua string) (*ghRelease, error) {
	client := &http.Client{Timeout: 15 * time.Second}
	req, _ := http.NewRequest("GET", apiURL, nil)
	req.Header.Set("User-Agent", ua+"/1.0")
	req.Header.Set("Accept", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch %s: %w", apiURL, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("API returned HTTP %d for %s", resp.StatusCode, apiURL)
	}
	var rel ghRelease
	if err := json.NewDecoder(resp.Body).Decode(&rel); err != nil {
		return nil, fmt.Errorf("decode release JSON: %w", err)
	}
	return &rel, nil
}

// fetchGHRelease kept for compatibility.
func fetchGHRelease(apiURL, ua string) (*ghRelease, error) {
	rels, err := fetchReleaseList(apiURL, ua)
	if err != nil {
		return nil, err
	}
	if len(rels) == 0 {
		return nil, fmt.Errorf("no releases at %s", apiURL)
	}
	return &rels[0], nil
}

func downloadToTemp(url string) (string, error) {
	client := &http.Client{Timeout: 10 * time.Minute}
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "forgejo-forge/1.0")
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("server returned HTTP %d", resp.StatusCode)
	}
	tmp, err := os.CreateTemp("", "runner-*")
	if err != nil {
		return "", err
	}
	total := resp.ContentLength
	written := int64(0)
	buf := make([]byte, 32*1024)
	for {
		n, err := resp.Body.Read(buf)
		if n > 0 {
			if _, werr := tmp.Write(buf[:n]); werr != nil {
				tmp.Close()
				os.Remove(tmp.Name())
				return "", werr
			}
			written += int64(n)
			if total > 0 {
				fmt.Printf("\r  Downloading... %.1f%%", float64(written)/float64(total)*100)
			}
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			tmp.Close()
			os.Remove(tmp.Name())
			return "", err
		}
	}
	fmt.Println()
	tmp.Close()
	return tmp.Name(), nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}
