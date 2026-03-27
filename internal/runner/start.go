package runner

import (
	"fmt"
	"os"
	"os/exec"
)

// StartBackground launches `gitea web --config <iniPath>` as a detached
// background process, redirecting stdout+stderr to logFile.
// GITEA_WORK_DIR is set so Gitea resolves paths correctly.
// Returns the child PID.
func StartBackground(giteaBin, iniPath, logFile, workDir string) (int, error) {
	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o640)
	if err != nil {
		return 0, fmt.Errorf("open log file: %w", err)
	}

	cmd := exec.Command(giteaBin, "web", "--config", iniPath)
	cmd.Stdout = f
	cmd.Stderr = f
	cmd.Env = append(os.Environ(), "GITEA_WORK_DIR="+workDir)

	if err := cmd.Start(); err != nil {
		f.Close()
		return 0, fmt.Errorf("start gitea: %w", err)
	}

	// Detach: let the child live independently.
	go func() {
		_ = cmd.Wait()
		f.Close()
	}()

	return cmd.Process.Pid, nil
}

// KillExisting sends SIGTERM to any running `gitea web` process via pkill.
// Silently ignores "no process found" errors.
func KillExisting() {
	_ = exec.Command("pkill", "-f", "gitea web").Run()
}
