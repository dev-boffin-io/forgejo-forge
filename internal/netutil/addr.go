package netutil

import (
	"bufio"
	"fmt"
	"net"
	"os/exec"
	"regexp"
	"strings"
	"time"
)

// oneSecond and sleep are defined here so port.go can reference them.
const oneSecond = time.Second

func sleep(d time.Duration) { time.Sleep(d) }

// LANAddresses returns all non-loopback IPv4 addresses of the current host.
func LANAddresses() []string {
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil
	}
	var addrs []string
	for _, iface := range ifaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}
		ifAddrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, a := range ifAddrs {
			var ip net.IP
			switch v := a.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}
			if ip == nil || ip.IsLoopback() {
				continue
			}
			if ip4 := ip.To4(); ip4 != nil {
				addrs = append(addrs, ip4.String())
			}
		}
	}
	return addrs
}

// CloudflaredURL tries to read the public tunnel URL from a running cloudflared
// process. Returns empty string if cloudflared is not running.
func CloudflaredURL() string {
	// cloudflared exposes its metrics on localhost:2000 by default.
	conn, err := net.DialTimeout("tcp", "127.0.0.1:2000", 500*time.Millisecond)
	if err != nil {
		return ""
	}
	conn.Close()

	// Ask cloudflared for its tunnel URL via the metrics API.
	out, err := exec.Command("curl", "-sf", "http://127.0.0.1:2000/metrics").Output()
	if err != nil {
		return ""
	}

	re := regexp.MustCompile(`https://[a-z0-9\-]+\.trycloudflare\.com`)
	if m := re.Find(out); m != nil {
		return string(m)
	}

	// Fallback: scan tunnel info file if it exists.
	return cloudflaredFromLog()
}

var cfURLRe = regexp.MustCompile(`https://[^\s]+\.trycloudflare\.com`)

func cloudflaredFromLog() string {
	out, err := exec.Command("journalctl", "-u", "cloudflared", "--no-pager", "-n", "50").Output()
	if err != nil {
		return ""
	}
	sc := bufio.NewScanner(strings.NewReader(string(out)))
	for sc.Scan() {
		if m := cfURLRe.FindString(sc.Text()); m != "" {
			return m
		}
	}
	return ""
}

// PrintAccessURLs prints localhost, LAN, and cloudflared URLs for a given port.
func PrintAccessURLs(port int) {
	fmt.Printf("🌐 Local:  http://localhost:%d\n", port)

	for _, ip := range LANAddresses() {
		fmt.Printf("🌐 LAN:    http://%s:%d\n", ip, port)
	}

	if u := CloudflaredURL(); u != "" {
		fmt.Printf("☁  Tunnel: %s\n", u)
	}
}
