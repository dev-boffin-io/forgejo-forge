package arch

import "runtime"

// BinaryInfo describes which binary to download for a given platform.
type BinaryInfo struct {
	// Source is "forgejo" or "gitea" — determines download URL and API.
	Source string
	// Suffix is the asset name suffix used in the release filename.
	// e.g. "linux-amd64", "windows-4.0-amd64"
	Suffix string
}

// Primary returns the BinaryInfo for the current machine.
//
// Platform → binary mapping:
//
//	Linux  → Forgejo  (still ships Linux binaries)
//	Windows → Gitea   (Forgejo dropped Windows support in 2024)
//	macOS  → Gitea    (Forgejo only ships Linux)
func Primary() BinaryInfo {
	switch runtime.GOOS {
	case "windows":
		switch runtime.GOARCH {
		case "arm64":
			return BinaryInfo{Source: "gitea", Suffix: "windows-4.0-arm64"}
		default: // amd64 and anything else
			return BinaryInfo{Source: "gitea", Suffix: "windows-4.0-amd64"}
		}
	case "darwin":
		switch runtime.GOARCH {
		case "arm64":
			return BinaryInfo{Source: "gitea", Suffix: "darwin-10.12-arm64"}
		default:
			return BinaryInfo{Source: "gitea", Suffix: "darwin-10.12-amd64"}
		}
	default: // linux
		switch runtime.GOARCH {
		case "arm64":
			return BinaryInfo{Source: "forgejo", Suffix: "linux-arm64"}
		case "arm":
			return BinaryInfo{Source: "forgejo", Suffix: "linux-arm-6"}
		default: // amd64
			return BinaryInfo{Source: "forgejo", Suffix: "linux-amd64"}
		}
	}
}

// Fallbacks returns an ordered list of BinaryInfos to try,
// starting with the primary one.
func Fallbacks(primary BinaryInfo) []BinaryInfo {
	switch primary.Suffix {
	// Linux fallback chain
	case "linux-arm64":
		return []BinaryInfo{
			{Source: "forgejo", Suffix: "linux-arm64"},
			{Source: "forgejo", Suffix: "linux-arm-6"},
			{Source: "forgejo", Suffix: "linux-amd64"},
		}
	case "linux-amd64":
		return []BinaryInfo{primary}

	// Windows fallback: arm64 → amd64
	case "windows-4.0-arm64":
		return []BinaryInfo{
			{Source: "gitea", Suffix: "windows-4.0-arm64"},
			{Source: "gitea", Suffix: "windows-4.0-amd64"},
		}
	case "windows-4.0-amd64":
		return []BinaryInfo{primary}

	default:
		return []BinaryInfo{primary}
	}
}

// BinName returns the installed binary name for the current OS/source.
// On Windows both forgejo and gitea get .exe extension.
func BinName(source string) string {
	if runtime.GOOS == "windows" {
		return source + ".exe"
	}
	return source
}
