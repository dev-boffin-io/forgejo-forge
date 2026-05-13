package install

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"

	"github.com/dev-boffin-io/forgejo-installer/internal/arch"
)

// installDir returns the best install directory for the current OS.
func installDir(source string) string {
	if runtime.GOOS == "windows" {
		// %LOCALAPPDATA%\Programs\<source> — no admin required
		localAppData := os.Getenv("LOCALAPPDATA")
		if localAppData != "" {
			return filepath.Join(localAppData, "Programs", source)
		}
		exe, err := os.Executable()
		if err == nil {
			return filepath.Dir(exe)
		}
		return "."
	}
	return "/usr/local/bin"
}

// Destination returns the full install path for a given source binary.
func Destination(source string) string {
	return filepath.Join(installDir(source), arch.BinName(source))
}

// ValidateBinary runs `<binary> --version` to confirm the file is executable.
func ValidateBinary(path string) error {
	if runtime.GOOS != "windows" {
		if err := os.Chmod(path, 0755); err != nil {
			return fmt.Errorf("chmod: %w", err)
		}
	}
	out, err := exec.Command(path, "--version").CombinedOutput()
	if err != nil {
		return fmt.Errorf("self-test failed: %w\noutput: %s", err, out)
	}
	return nil
}

// MoveToDest installs tmpPath to the correct destination for source.
func MoveToDest(tmpPath, source string) error {
	dest := Destination(source)
	dir := filepath.Dir(dest)

	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("create install dir %s: %w", dir, err)
	}

	if isWritable(dir) {
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

	return fmt.Errorf("cannot write to %s — try running as Administrator", dir)
}

// RemoveBinary removes the installed binary for source.
func RemoveBinary(source string) error {
	dest := Destination(source)

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

	return fmt.Errorf("cannot remove %s — try running as Administrator", dest)
}

// ── helpers ───────────────────────────────────────────────────────────────────

func isWritable(dir string) bool {
	probe := filepath.Join(dir, ".forge-write-test")
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
	// Cross-device: copy then remove
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
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
	}
	return os.Remove(src)
}
