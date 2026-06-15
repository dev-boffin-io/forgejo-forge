//go:build windows

package cmd

import (
	"os/exec"
	"syscall"
)

const runnerDetachedProcess = 0x00000008

func setSysProcAttr(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: runnerDetachedProcess | syscall.CREATE_NEW_PROCESS_GROUP,
	}
}
