package version

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os/exec"
	"regexp"
	"strings"
	"time"
)

// Forgejo latest release via Codeberg Forgejo API.
const apiURL = "https://codeberg.org/api/v1/repos/forgejo/forgejo/releases/latest"

var semverRe = regexp.MustCompile(`\b(\d+)\.(\d+)\.(\d+)\b`)

// httpClient with a sane timeout — avoids hanging forever.
var httpClient = &http.Client{Timeout: 15 * time.Second}

// Latest fetches the latest Forgejo release version from Codeberg.
// Returns a plain semver string like "9.0.3".
func Latest() (string, error) {
	resp, err := httpClient.Get(apiURL)
	if err != nil {
		return "", fmt.Errorf("fetch latest release: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("unexpected HTTP %d from Codeberg API", resp.StatusCode)
	}

	var release struct {
		TagName string `json:"tag_name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return "", fmt.Errorf("decode response: %w", err)
	}

	// tag_name is like "v9.0.3" — strip leading 'v'
	ver := strings.TrimPrefix(release.TagName, "v")
	if semverRe.FindString(ver) == "" {
		return "", fmt.Errorf("unexpected tag format: %q", release.TagName)
	}
	return ver, nil
}

// Installed returns the version reported by a locally installed forgejo binary,
// or "none" if forgejo is not found in PATH.
func Installed() string {
	path, err := exec.LookPath("forgejo")
	if err != nil {
		return "none"
	}

	out, err := exec.Command(path, "--version").Output()
	if err != nil {
		return "none"
	}

	// "Forgejo version 9.0.3 built with..."
	m := semverRe.FindString(string(out))
	if m == "" {
		return "none"
	}
	return m
}
