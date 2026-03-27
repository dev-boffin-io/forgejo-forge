package arch

import "runtime"

// Primary returns the Gitea asset suffix for the current machine.
func Primary() string {
	switch runtime.GOARCH {
	case "arm64":
		return "linux-arm64"
	case "amd64":
		return "linux-amd64"
	case "arm":
		return "linux-arm-7"
	default:
		return "linux-" + runtime.GOARCH
	}
}

// Fallbacks returns an ordered list of architectures to try,
// starting with the primary one. On ARM64 we also attempt arm-7
// and amd64 (via binfmt/qemu) as last resorts.
func Fallbacks(primary string) []string {
	switch primary {
	case "linux-arm64":
		return []string{"linux-arm64", "linux-arm-7", "linux-amd64"}
	case "linux-amd64":
		return []string{"linux-amd64"}
	default:
		return []string{primary}
	}
}
