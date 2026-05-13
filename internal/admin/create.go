package admin

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

// CreateOptions holds parameters for the admin user create command.
type CreateOptions struct {
	ForgejoBin string // path to forgejo or gitea binary
	IniPath    string
	WorkDir    string
	Username   string
	Password   string
	Email      string
}

// CreateUser runs `<binary> admin user create` with the given options.
// Works for both Forgejo (Linux) and Gitea (Windows).
// Returns nil if the user was created or already exists.
func CreateUser(opts CreateOptions) error {
	fmt.Printf("▶ Creating admin user %q...\n", opts.Username)

	args := []string{
		"admin", "user", "create",
		"--config", opts.IniPath,
		"--username", opts.Username,
		"--password", opts.Password,
		"--email", opts.Email,
		"--must-change-password=false",
		"--admin",
	}

	cmd := exec.Command(opts.ForgejoBin, args...)

	workDir := opts.WorkDir
	if workDir == "" {
		workDir = filepath.Dir(filepath.Dir(opts.IniPath))
	}

	// Both Forgejo and Gitea respect their respective WORK_DIR env vars.
	// Set both so it works regardless of which binary is in use.
	env := os.Environ()
	if runtime.GOOS == "windows" {
		// Gitea on Windows
		env = append(env, "GITEA_WORK_DIR="+workDir)
	} else {
		// Forgejo on Linux
		env = append(env, "FORGEJO_WORK_DIR="+workDir)
	}
	cmd.Env = env

	out, err := cmd.CombinedOutput()
	if err != nil {
		msg := strings.ToLower(string(out))
		if strings.Contains(msg, "user already exists") ||
			strings.Contains(msg, "already been taken") {
			fmt.Println("⚠ Admin user already exists, skipping")
			return nil
		}
		return fmt.Errorf("admin user create: %w\n%s", err, out)
	}

	fmt.Println("✔ Admin user created")
	return nil
}

// DefaultEmail returns a safe fallback email from a username.
func DefaultEmail(username string) string {
	if username == "" {
		return "admin@example.com"
	}
	if strings.Contains(username, "@") {
		return username
	}
	return username + "@example.com"
}

// Validate checks that required fields are non-empty.
func Validate(opts CreateOptions) error {
	var errs []string
	if opts.Username == "" {
		errs = append(errs, "--username is required")
	}
	if opts.Password == "" {
		errs = append(errs, "--password is required")
	}
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}
