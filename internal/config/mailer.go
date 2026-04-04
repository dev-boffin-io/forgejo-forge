package config

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// MailerParams holds all values for the [mailer] section of app.ini.
type MailerParams struct {
	Enabled  bool
	From     string
	Protocol string // "smtps" (port 465) or "smtp" (port 587 STARTTLS)
	SMTPAddr string
	SMTPPort int
	User     string
	Passwd   string
}

// WriteMailer patches (or appends) the [mailer] section in an existing app.ini.
// The config file must already exist — run 'forgejo-forge setup' first.
func WriteMailer(iniPath string, p MailerParams) error {
	if _, err := os.Stat(iniPath); os.IsNotExist(err) {
		return fmt.Errorf("config not found: %s\n  → run 'forgejo-forge setup' first", iniPath)
	}

	section := fmt.Sprintf("[mailer]\nENABLED   = %v\nFROM      = %s\nPROTOCOL  = %s\nSMTP_ADDR = %s\nSMTP_PORT = %d\nUSER      = %s\nPASSWD    = %s\n",
		p.Enabled, p.From, p.Protocol, p.SMTPAddr, p.SMTPPort, p.User, p.Passwd)

	return patchSection(iniPath, "mailer", section)
}

// ReadMailer reads [mailer] values from an existing app.ini.
// Returns sensible defaults (smtps / port 465) when the section is absent.
func ReadMailer(iniPath string) MailerParams {
	p := MailerParams{Protocol: "smtps", SMTPPort: 465}
	f, err := os.Open(iniPath)
	if err != nil {
		return p
	}
	defer f.Close()

	inSection := false
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if strings.HasPrefix(line, "[") {
			inSection = strings.TrimSpace(strings.Trim(line, "[]")) == "mailer"
			continue
		}
		if !inSection || line == "" || strings.HasPrefix(line, ";") || strings.HasPrefix(line, "#") {
			continue
		}
		kv := strings.SplitN(line, "=", 2)
		if len(kv) != 2 {
			continue
		}
		key := strings.TrimSpace(kv[0])
		val := strings.TrimSpace(kv[1])
		switch key {
		case "ENABLED":
			p.Enabled = strings.EqualFold(val, "true")
		case "FROM":
			p.From = val
		case "PROTOCOL":
			p.Protocol = val
		case "SMTP_ADDR":
			p.SMTPAddr = val
		case "SMTP_PORT":
			fmt.Sscanf(val, "%d", &p.SMTPPort)
		case "USER":
			p.User = val
		case "PASSWD":
			p.Passwd = val
		}
	}
	return p
}

// patchSection replaces an existing [sectionName] block in iniPath,
// or appends it at the end if not found.
func patchSection(iniPath, sectionName, newSection string) error {
	f, err := os.Open(iniPath)
	if err != nil {
		return fmt.Errorf("read %s: %w", iniPath, err)
	}
	var lines []string
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		lines = append(lines, sc.Text())
	}
	f.Close()

	header := "[" + sectionName + "]"
	start := -1
	end := len(lines)

	for i, l := range lines {
		trimmed := strings.TrimSpace(l)
		if trimmed == header {
			start = i
			continue
		}
		if start >= 0 && i > start && strings.HasPrefix(trimmed, "[") {
			end = i
			break
		}
	}

	newLines := strings.Split(strings.TrimRight(newSection, "\n"), "\n")
	var result []string
	if start >= 0 {
		// Replace existing section (lines[start:end])
		result = append(result, lines[:start]...)
		result = append(result, newLines...)
		result = append(result, lines[end:]...)
	} else {
		// Append new section with a blank separator line
		result = append(lines, "")
		result = append(result, newLines...)
	}

	content := strings.Join(result, "\n") + "\n"
	return os.WriteFile(iniPath, []byte(content), 0o640)
}
