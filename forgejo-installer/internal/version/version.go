package version

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os/exec"
	"regexp"
	"runtime"
	"strings"
	"time"

	"github.com/dev-boffin-io/forgejo-installer/internal/arch"
)

const (
	forgejoAPI = "https://codeberg.org/api/v1/repos/forgejo/forgejo/releases/latest"
	giteaAPI   = "https://api.github.com/repos/go-gitea/gitea/releases/latest"
)

var semverRe = regexp.MustCompile(`\b(\d+)\.(\d+)\.(\d+)\b`)
var httpClient = &http.Client{Timeout: 15 * time.Second}

// LatestForSource fetches the latest release version for "forgejo" or "gitea".
func LatestForSource(source string) (string, error) {
	switch source {
	case "gitea":
		return latestGitea()
	default:
		return latestForgejo()
	}
}

// Latest fetches the latest version for the current platform's default source.
func Latest() (string, error) {
	info := arch.Primary()
	return LatestForSource(info.Source)
}

func latestForgejo() (string, error) {
	resp, err := httpClient.Get(forgejoAPI)
	if err != nil {
		return "", fmt.Errorf("fetch Forgejo release: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("Codeberg API returned HTTP %d", resp.StatusCode)
	}

	var release struct {
		TagName string `json:"tag_name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return "", fmt.Errorf("decode Forgejo response: %w", err)
	}

	ver := strings.TrimPrefix(release.TagName, "v")
	if semverRe.FindString(ver) == "" {
		return "", fmt.Errorf("unexpected Forgejo tag: %q", release.TagName)
	}
	return ver, nil
}

func latestGitea() (string, error) {
	req, err := http.NewRequest("GET", giteaAPI, nil)
	if err != nil {
		return "", err
	}
	// GitHub API requires a User-Agent header
	req.Header.Set("User-Agent", "forgejo-installer/1.0")
	req.Header.Set("Accept", "application/vnd.github+json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("fetch Gitea release: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("GitHub API returned HTTP %d", resp.StatusCode)
	}

	var release struct {
		TagName string `json:"tag_name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return "", fmt.Errorf("decode Gitea response: %w", err)
	}

	ver := strings.TrimPrefix(release.TagName, "v")
	if semverRe.FindString(ver) == "" {
		return "", fmt.Errorf("unexpected Gitea tag: %q", release.TagName)
	}
	return ver, nil
}

// Installed returns the version of the installed binary (forgejo or gitea),
// or "none" if neither is found in PATH.
func Installed() string {
	info := arch.Primary()
	return installedVersion(info.Source)
}

func installedVersion(source string) string {
	candidates := []string{source}
	if runtime.GOOS == "windows" {
		candidates = []string{source + ".exe", source}
	}

	for _, name := range candidates {
		path, err := exec.LookPath(name)
		if err != nil {
			continue
		}
		out, err := exec.Command(path, "--version").Output()
		if err != nil {
			continue
		}
		if m := semverRe.FindString(string(out)); m != "" {
			return m
		}
	}
	return "none"
}
