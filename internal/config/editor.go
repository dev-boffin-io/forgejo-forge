package config

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strings"
)

// SetKey sets key=value within [section] of iniPath, creating the section
// if it doesn't exist. Existing keys in the section are preserved; only the
// given key is added or overwritten. Key order within the section is
// alphabetical for new sections, and preserved (with the new/updated key
// appended) for existing sections.
func SetKey(iniPath, section, key, value string) error {
	if err := Exists(iniPath); err != nil {
		return err
	}
	kv, order, err := readSection(iniPath, section)
	if err != nil {
		return err
	}
	if _, exists := kv[key]; !exists {
		order = append(order, key)
	}
	kv[key] = value
	return writeSectionKV(iniPath, section, kv, order)
}

// RemoveKey deletes key from [section] of iniPath. If the section becomes
// empty as a result, the section header itself is also removed.
// Returns (removed bool, error) — removed=false if the key wasn't present.
func RemoveKey(iniPath, section, key string) (bool, error) {
	if err := Exists(iniPath); err != nil {
		return false, err
	}
	kv, order, err := readSection(iniPath, section)
	if err != nil {
		return false, err
	}
	if _, exists := kv[key]; !exists {
		return false, nil
	}
	delete(kv, key)
	newOrder := order[:0:0]
	for _, k := range order {
		if k != key {
			newOrder = append(newOrder, k)
		}
	}
	if len(newOrder) == 0 {
		// Remove the whole section.
		return true, removeSection(iniPath, section)
	}
	return true, writeSectionKV(iniPath, section, kv, newOrder)
}

// GetKey returns the value of key in [section], and whether it was found.
func GetKey(iniPath, section, key string) (string, bool, error) {
	if err := Exists(iniPath); err != nil {
		return "", false, err
	}
	kv, _, err := readSection(iniPath, section)
	if err != nil {
		return "", false, err
	}
	v, ok := kv[key]
	return v, ok, nil
}

// ListSection returns all key=value pairs in [section], in file order.
// Returns an empty (non-nil) slice if the section doesn't exist.
type KV struct {
	Key   string
	Value string
}

func ListSection(iniPath, section string) ([]KV, error) {
	if err := Exists(iniPath); err != nil {
		return nil, err
	}
	kv, order, err := readSection(iniPath, section)
	if err != nil {
		return nil, err
	}
	out := make([]KV, 0, len(order))
	for _, k := range order {
		out = append(out, KV{Key: k, Value: kv[k]})
	}
	return out, nil
}

// ListSections returns the names of every [section] header in iniPath, in
// file order, without duplicates.
func ListSections(iniPath string) ([]string, error) {
	if err := Exists(iniPath); err != nil {
		return nil, err
	}
	f, err := os.Open(iniPath)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", iniPath, err)
	}
	defer f.Close()

	seen := map[string]bool{}
	var out []string
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			name := strings.TrimSpace(strings.Trim(line, "[]"))
			if name != "" && !seen[name] {
				seen[name] = true
				out = append(out, name)
			}
		}
	}
	return out, nil
}

// ── internal helpers ─────────────────────────────────────────────────────────

// readSection parses [section] from iniPath into a key→value map plus the
// original key order. Comments and blank lines within the section are
// dropped (re-written sections are normalized). Returns empty results if
// the section doesn't exist (not an error).
func readSection(iniPath, section string) (map[string]string, []string, error) {
	f, err := os.Open(iniPath)
	if err != nil {
		return nil, nil, fmt.Errorf("read %s: %w", iniPath, err)
	}
	defer f.Close()

	header := "[" + section + "]"
	kv := map[string]string{}
	var order []string
	inSection := false

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			inSection = line == header
			continue
		}
		if !inSection || line == "" || strings.HasPrefix(line, ";") || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])
		if _, exists := kv[key]; !exists {
			order = append(order, key)
		}
		kv[key] = val
	}
	return kv, order, nil
}

// writeSectionKV rewrites [section] in iniPath with the given key/value
// pairs, using order for key ordering (any keys in kv not present in order
// are appended alphabetically).
func writeSectionKV(iniPath, section string, kv map[string]string, order []string) error {
	inOrder := map[string]bool{}
	for _, k := range order {
		inOrder[k] = true
	}
	var extra []string
	for k := range kv {
		if !inOrder[k] {
			extra = append(extra, k)
		}
	}
	sort.Strings(extra)
	order = append(order, extra...)

	var b strings.Builder
	fmt.Fprintf(&b, "[%s]\n", section)
	for _, k := range order {
		fmt.Fprintf(&b, "%s = %s\n", k, kv[k])
	}
	return patchSection(iniPath, section, b.String())
}

// removeSection deletes an entire [section] block (header + contents) from
// iniPath. No-op if the section doesn't exist.
func removeSection(iniPath, section string) error {
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

	header := "[" + section + "]"
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
	if start < 0 {
		return nil // nothing to remove
	}

	var result []string
	result = append(result, lines[:start]...)
	result = append(result, lines[end:]...)

	// Trim a leftover blank separator line directly above the removed
	// section, if any, to avoid accumulating empty lines.
	for len(result) > 0 && start > 0 && start-1 == len(result)-1 && strings.TrimSpace(result[len(result)-1]) == "" {
		result = result[:len(result)-1]
		break
	}

	content := strings.Join(result, "\n")
	if !strings.HasSuffix(content, "\n") {
		content += "\n"
	}
	return os.WriteFile(iniPath, []byte(content), 0o640)
}
