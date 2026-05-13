package cmd

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"runtime"
	"time"

	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var logsFollow bool
var logsLines int

var logsCmd = &cobra.Command{
	Use:   "logs",
	Short: "Show or follow Forgejo logs",
	RunE:  runLogs,
}

func init() {
	logsCmd.Flags().BoolVarP(&logsFollow, "follow", "f", true, "Follow log output")
	logsCmd.Flags().IntVarP(&logsLines, "lines", "n", 50, "Number of lines to show")
}

func runLogs(_ *cobra.Command, _ []string) error {
	mode := detect.Env()

	switch mode {
	case detect.ModeSystemd:
		return logsSystemd()
	case detect.ModeWindows:
		return logsFile(detect.ModeWindows)
	default:
		return logsProot()
	}
}

func logsSystemd() error {
	args := []string{"-u", "forgejo", "--no-pager", "-n", fmt.Sprintf("%d", logsLines)}
	if logsFollow {
		args = append(args, "-f")
	}
	cmd := exec.Command("journalctl", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func logsProot() error {
	paths, err := svc.Resolve(detect.ModeProot)
	if err != nil {
		return err
	}

	if _, err := os.Stat(paths.LogFile); os.IsNotExist(err) {
		return fmt.Errorf("log file not found: %s", paths.LogFile)
	}

	// Use tail on Linux/macOS; fall back to pure-Go reader on Windows
	if runtime.GOOS != "windows" {
		args := []string{fmt.Sprintf("-n%d", logsLines)}
		if logsFollow {
			args = append(args, "-f")
		}
		args = append(args, paths.LogFile)
		cmd := exec.Command("tail", args...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		return cmd.Run()
	}

	return logsFile(detect.ModeProot)
}

// logsFile is a pure-Go log reader used on Windows (no `tail` available).
func logsFile(mode detect.Mode) error {
	paths, err := svc.Resolve(mode)
	if err != nil {
		return err
	}

	if _, err := os.Stat(paths.LogFile); os.IsNotExist(err) {
		return fmt.Errorf("log file not found: %s", paths.LogFile)
	}

	printLastLines(paths.LogFile, logsLines)

	if !logsFollow {
		return nil
	}

	// Follow: poll for new lines every 500ms
	f, err := os.Open(paths.LogFile)
	if err != nil {
		return fmt.Errorf("open log: %w", err)
	}
	defer f.Close()

	// Seek to end
	if _, err := f.Seek(0, io.SeekEnd); err != nil {
		return err
	}

	fmt.Println("--- following log (Ctrl+C to quit) ---")
	sc := bufio.NewScanner(f)
	for {
		for sc.Scan() {
			fmt.Println(sc.Text())
		}
		time.Sleep(500 * time.Millisecond)
	}
}

// printLastLines prints the last n lines of a file using pure Go.
// Used on Windows where `tail` is not available.
func printLastLines(path string, n int) {
	f, err := os.Open(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "⚠ Cannot open log file: %v\n", err)
		return
	}
	defer f.Close()

	var lines []string
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		lines = append(lines, sc.Text())
	}

	start := 0
	if len(lines) > n {
		start = len(lines) - n
	}
	for _, l := range lines[start:] {
		fmt.Println(l)
	}
}
