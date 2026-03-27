package version

import (
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"regexp"
	"sort"
	"strings"
	"time"
)

const indexURL = "https://dl.gitea.com/gitea/"

var semverRe = regexp.MustCompile(`\b(\d+)\.(\d+)\.(\d+)\b`)

// httpClient with a sane timeout — avoids hanging forever.
var httpClient = &http.Client{Timeout: 15 * time.Second}

// Latest scrapes the Gitea download index and returns the highest
// semantic version found. Returns an error if the page is unreachable
// or no version is detected.
func Latest() (string, error) {
	resp, err := httpClient.Get(indexURL)
	if err != nil {
		return "", fmt.Errorf("fetch index: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("unexpected HTTP %d from %s", resp.StatusCode, indexURL)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read index body: %w", err)
	}

	matches := semverRe.FindAllString(string(body), -1)
	if len(matches) == 0 {
		return "", fmt.Errorf("no version found in index page")
	}

	// Deduplicate then sort semantically.
	seen := make(map[string]struct{})
	var versions []string
	for _, v := range matches {
		if _, ok := seen[v]; !ok {
			seen[v] = struct{}{}
			versions = append(versions, v)
		}
	}
	sort.Slice(versions, func(i, j int) bool {
		return semverLess(versions[i], versions[j])
	})

	return versions[len(versions)-1], nil
}

// Installed returns the version string reported by a locally installed
// Gitea binary, or "none" if Gitea is not found in PATH.
func Installed() string {
	path, err := exec.LookPath("gitea")
	if err != nil {
		return "none"
	}

	out, err := exec.Command(path, "--version").Output()
	if err != nil {
		return "none"
	}

	// "Gitea version 1.22.0 built with..."
	m := semverRe.FindString(string(out))
	if m == "" {
		return "none"
	}
	return m
}

// semverLess compares two "X.Y.Z" strings numerically.
func semverLess(a, b string) bool {
	pa, pb := parseSemver(a), parseSemver(b)
	for i := range pa {
		if pa[i] != pb[i] {
			return pa[i] < pb[i]
		}
	}
	return false
}

func parseSemver(s string) [3]int {
	var major, minor, patch int
	parts := strings.SplitN(s, ".", 3)
	if len(parts) == 3 {
		fmt.Sscanf(parts[0], "%d", &major)
		fmt.Sscanf(parts[1], "%d", &minor)
		fmt.Sscanf(parts[2], "%d", &patch)
	}
	return [3]int{major, minor, patch}
}
