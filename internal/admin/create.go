package admin

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// CreateOptions holds parameters for the admin user create command.
type CreateOptions struct {
	GiteaBin string
	IniPath  string
	WorkDir  string // GITEA_WORK_DIR — must match WORK_PATH in app.ini
	Username string
	Password string
	Email    string
}

// CreateUser runs `gitea admin user create` with the given options.
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

	cmd := exec.Command(opts.GiteaBin, args...)

	// Gitea resolves paths relative to GITEA_WORK_DIR.
	// Without this, it falls back to its compiled-in default and
	// fails to find the config even when --config is supplied.
	workDir := opts.WorkDir
	if workDir == "" {
		workDir = filepath.Dir(filepath.Dir(opts.IniPath)) // …/custom/conf → …
	}
	cmd.Env = append(os.Environ(), "GITEA_WORK_DIR="+workDir)

	out, err := cmd.CombinedOutput()
	if err != nil {
		msg := strings.ToLower(string(out))
		if strings.Contains(msg, "user already exists") ||
			strings.Contains(msg, "already been taken") {
			fmt.Println("⚠ Admin user already exists, skipping")
			return nil
		}
		return fmt.Errorf("gitea admin user create: %w\n%s", err, out)
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
