//go:build windows

package runner

import (
	"os/exec"
	"syscall"
)

// setSysProcAttr sets Windows-specific process attributes to detach the child
// from the current console window so it keeps running after the parent exits.
func setSysProcAttr(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: syscall.CREATE_NEW_PROCESS_GROUP,
	}
}
