package runner

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
)

// StartBackground launches the forge binary (forgejo or gitea) as a detached
// background process, redirecting stdout+stderr to logFile.
// The appropriate WORK_DIR env var is set for the binary.
// On Windows the PID is written to pidFile for later stop/restart.
// Returns the child PID.
func StartBackground(forgejoBin, iniPath, logFile, workDir string, pidFile ...string) (int, error) {
	if err := os.MkdirAll(logFileDir(logFile), 0o750); err != nil {
		return 0, fmt.Errorf("create log dir: %w", err)
	}

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o640)
	if err != nil {
		return 0, fmt.Errorf("open log file: %w", err)
	}

	cmd := exec.Command(forgejoBin, "web", "--config", iniPath)
	cmd.Stdout = f
	cmd.Stderr = f

	// Set the correct work dir env var depending on which binary is used.
	// Gitea uses GITEA_WORK_DIR; Forgejo uses FORGEJO_WORK_DIR.
	env := os.Environ()
	if runtime.GOOS == "windows" {
		env = append(env, "GITEA_WORK_DIR="+workDir)
	} else {
		env = append(env, "FORGEJO_WORK_DIR="+workDir)
	}
	cmd.Env = env

	// Platform-specific process detach (sysproc_*.go)
	setSysProcAttr(cmd)

	if err := cmd.Start(); err != nil {
		f.Close()
		return 0, fmt.Errorf("start binary: %w", err)
	}

	pid := cmd.Process.Pid

	// Persist PID so stop/restart can find it on Windows.
	if len(pidFile) > 0 && pidFile[0] != "" {
		_ = os.WriteFile(pidFile[0], []byte(strconv.Itoa(pid)), 0o644)
	}

	// Detach: let the child live independently.
	go func() {
		_ = cmd.Wait()
		f.Close()
	}()

	return pid, nil
}

// KillExisting terminates any running forge web process.
// On Windows it reads the PID file and uses taskkill for gitea.exe.
// On Linux it uses pkill for forgejo.
func KillExisting(pidFile ...string) {
	if runtime.GOOS == "windows" {
		killWindows(pidFile...)
		return
	}
	_ = exec.Command("pkill", "-f", "forgejo web").Run()
}

// ── helpers ───────────────────────────────────────────────────────────────────

func logFileDir(logFile string) string {
	if logFile == "" {
		return "."
	}
	for i := len(logFile) - 1; i >= 0; i-- {
		if logFile[i] == '/' || logFile[i] == '\\' {
			return logFile[:i]
		}
	}
	return "."
}

func killWindows(pidFile ...string) {
	// Try PID file first (clean shutdown).
	if len(pidFile) > 0 && pidFile[0] != "" {
		data, err := os.ReadFile(pidFile[0])
		if err == nil {
			pidStr := strings.TrimSpace(string(data))
			if pid, err := strconv.Atoi(pidStr); err == nil {
				if proc, err := os.FindProcess(pid); err == nil {
					_ = proc.Kill()
				}
				_ = os.Remove(pidFile[0])
				return
			}
		}
	}
	// Fallback: taskkill by image name (gitea on Windows).
	_ = exec.Command("taskkill", "/F", "/IM", "gitea.exe").Run()
}
