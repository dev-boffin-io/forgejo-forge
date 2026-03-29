package install

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

const (
	binName    = "gitea"
	installDir = "/usr/local/bin"
)

// Destination returns the full install path
func Destination() string {
	return filepath.Join(installDir, binName)
}

// ─── Validate ────────────────────────────────────────────────────────────────

func ValidateBinary(path string) error {
	if err := os.Chmod(path, 0755); err != nil {
		return fmt.Errorf("chmod: %w", err)
	}

	out, err := exec.Command(path, "--version").CombinedOutput()
	if err != nil {
		return fmt.Errorf("binary self-test failed: %w\noutput: %s", err, out)
	}
	return nil
}

// ─── Install ─────────────────────────────────────────────────────────────────

func MoveToDest(tmpPath string) error {
	dest := Destination()

	if isWritable(installDir) {
		return moveFile(tmpPath, dest)
	}

	if runtime.GOOS == "linux" {
		cmd := exec.Command("sudo", "mv", tmpPath, dest)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("sudo mv: %w", err)
		}
		return nil
	}

	return fmt.Errorf("cannot write to %s and sudo unavailable", installDir)
}

// ─── Uninstall ───────────────────────────────────────────────────────────────

func RemoveBinary() error {
	dest := Destination()

	if _, err := os.Stat(dest); os.IsNotExist(err) {
		return fmt.Errorf("binary not found at %s", dest)
	}

	if isWritable(filepath.Dir(dest)) {
		return os.Remove(dest)
	}

	if runtime.GOOS == "linux" {
		cmd := exec.Command("sudo", "rm", "-f", dest)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("sudo rm: %w", err)
		}
		return nil
	}

	return fmt.Errorf("cannot remove %s and sudo unavailable", dest)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

func isWritable(dir string) bool {
	probe := filepath.Join(dir, ".forgejo-write-test")
	f, err := os.OpenFile(probe, os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return false
	}
	f.Close()
	os.Remove(probe)
	return true
}

func moveFile(src, dst string) error {
	if err := os.Rename(src, dst); err == nil {
		return nil
	}

	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.OpenFile(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
	if err != nil {
		return err
	}
	defer out.Close()

	buf := make([]byte, 32*1024)
	for {
		n, err := in.Read(buf)
		if n > 0 {
			if _, werr := out.Write(buf[:n]); werr != nil {
				return werr
			}
		}
		if err != nil {
			break
		}
	}

	return os.Remove(src)
}
