//go:build !windows

package runner

import (
	"os/exec"
	"syscall"
)

// setSysProcAttr sets Unix-specific process attributes so the child is
// detached from the parent's process group and survives parent exit.
func setSysProcAttr(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setsid: true,
	}
}
