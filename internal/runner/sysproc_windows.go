//go:build windows

package runner

import (
	"os/exec"
	"syscall"
)

// DETACHED_PROCESS prevents the child from inheriting the parent's console,
// so gitea.exe runs silently in the background even after the parent exits.
// Combined with CREATE_NEW_PROCESS_GROUP so Ctrl+C signals are not forwarded.
const detachedProcess = 0x00000008 // DETACHED_PROCESS — not exported by syscall pkg

// setSysProcAttr sets Windows-specific process attributes to detach the child
// from the current console window so it keeps running after the parent exits.
func setSysProcAttr(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: detachedProcess | syscall.CREATE_NEW_PROCESS_GROUP,
	}
}
