package netutil

import (
	"fmt"
	"net"
	"time"
)

const oneSecond = time.Second

func sleep(d time.Duration) { time.Sleep(d) }

// FindFreePort returns the first free TCP port starting from preferredPort.
// Checks up to 20 ports before giving up.
func FindFreePort(preferredPort int) (int, error) {
	for port := preferredPort; port < preferredPort+20; port++ {
		if IsPortFree(port) {
			return port, nil
		}
	}
	return 0, fmt.Errorf("no free port found starting from %d", preferredPort)
}

// IsPortFree returns true when nothing is listening on 127.0.0.1:port.
func IsPortFree(port int) bool {
	ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
	if err != nil {
		return false
	}
	ln.Close()
	return true
}

// WaitForPort polls 127.0.0.1:port until it accepts connections or times out
// after maxRetries seconds.
func WaitForPort(port, maxRetries int) error {
	addr := fmt.Sprintf("127.0.0.1:%d", port)
	fmt.Printf("▶ Waiting for Forgejo on port %d", port)
	for i := range maxRetries {
		conn, err := net.DialTimeout("tcp", addr, oneSecond)
		if err == nil {
			conn.Close()
			fmt.Printf("\n✔ Forgejo is up (attempt %d)\n", i+1)
			return nil
		}
		fmt.Print(".")
		sleep(oneSecond)
	}
	fmt.Println()
	return fmt.Errorf("forgejo did not start within %ds", maxRetries)
}
