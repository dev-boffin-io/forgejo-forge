package download

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"runtime"
	"time"
)

// Source-specific download bases
const (
	forgejoBase = "https://codeberg.org/forgejo/forgejo/releases/download"
	giteaBase   = "https://dl.gitea.com/gitea"
)

var httpClient = &http.Client{Timeout: 5 * time.Minute}

// AssetURL builds the full download URL for a given source, version, and arch suffix.
//
//	Forgejo: https://codeberg.org/forgejo/forgejo/releases/download/v15.0.2/forgejo-15.0.2-linux-amd64
//	Gitea:   https://dl.gitea.com/gitea/1.26.1/gitea-1.26.1-windows-4.0-amd64.exe
func AssetURL(source, version, archSuffix string) string {
	ext := exeExt()
	switch source {
	case "gitea":
		// Gitea: https://dl.gitea.com/gitea/<version>/gitea-<version>-<arch>.exe
		return fmt.Sprintf("%s/%s/gitea-%s-%s%s",
			giteaBase, version, version, archSuffix, ext)
	default: // forgejo
		// Forgejo: https://codeberg.org/.../download/v<version>/forgejo-<version>-<arch>
		// Forgejo does NOT ship .exe — Linux only
		return fmt.Sprintf("%s/v%s/forgejo-%s-%s",
			forgejoBase, version, version, archSuffix)
	}
}

// Exists sends a HEAD request to check whether the asset URL is reachable.
func Exists(url string) bool {
	req, _ := http.NewRequest("HEAD", url, nil)
	req.Header.Set("User-Agent", "forgejo-installer/1.0")
	resp, err := httpClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

// ToFile downloads url into a new temp file and returns its path.
// Caller is responsible for removing the file when done.
// Progress is written to the provided writer (pass os.Stderr for terminal output).
func ToFile(url string, progress io.Writer) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", "forgejo-installer/1.0")

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("GET %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("server returned HTTP %d for %s", resp.StatusCode, url)
	}

	tmp, err := os.CreateTemp("", "forge-installer-*"+exeExt())
	if err != nil {
		return "", fmt.Errorf("create temp file: %w", err)
	}

	src := io.Reader(resp.Body)
	if progress != nil && resp.ContentLength > 0 {
		src = &progressReader{
			r:     resp.Body,
			total: resp.ContentLength,
			out:   progress,
		}
	}

	if _, err := io.Copy(tmp, src); err != nil {
		tmp.Close()
		os.Remove(tmp.Name())
		return "", fmt.Errorf("write temp file: %w", err)
	}

	if progress != nil {
		fmt.Fprintln(progress)
	}

	tmp.Close()
	return tmp.Name(), nil
}

// exeExt returns ".exe" on Windows, "" elsewhere.
func exeExt() string {
	if runtime.GOOS == "windows" {
		return ".exe"
	}
	return ""
}

// ── Simple progress reader ─────────────────────────────────────────────────────

type progressReader struct {
	r       io.Reader
	total   int64
	written int64
	out     io.Writer
}

func (p *progressReader) Read(buf []byte) (int, error) {
	n, err := p.r.Read(buf)
	p.written += int64(n)
	pct := float64(p.written) / float64(p.total) * 100
	fmt.Fprintf(p.out, "\r  Downloading... %.1f%%", pct)
	return n, err
}
