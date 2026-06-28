package cmd

import (
	"fmt"
	"io"
	"os"

	"github.com/dev-boffin-io/forgejo-forge/internal/config"
	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "View or edit app.ini settings (the file written by 'setup')",
}

var configPathCmd = &cobra.Command{
	Use:   "path",
	Short: "Print the resolved path to app.ini",
	RunE:  runConfigPath,
}

var configListCmd = &cobra.Command{
	Use:   "list <section>",
	Short: "List all key=value pairs in a section",
	Args:  cobra.ExactArgs(1),
	RunE:  runConfigList,
}

var configSectionsCmd = &cobra.Command{
	Use:   "sections",
	Short: "List all section names in app.ini",
	RunE:  runConfigSections,
}

var configGetCmd = &cobra.Command{
	Use:   "get <section> <key>",
	Short: "Print the value of a key in a section",
	Args:  cobra.ExactArgs(2),
	RunE:  runConfigGet,
}

var configSetCmd = &cobra.Command{
	Use:   "set <section> <key> <value>",
	Short: "Set (or add) key=value in a section, creating the section if needed",
	Args:  cobra.ExactArgs(3),
	RunE:  runConfigSet,
}

var configRemoveCmd = &cobra.Command{
	Use:   "remove <section> <key>",
	Short: "Remove a key from a section (removes the section too if it becomes empty)",
	Args:  cobra.ExactArgs(2),
	RunE:  runConfigRemove,
}

var configRawGetCmd = &cobra.Command{
	Use:   "raw-get",
	Short: "Print the entire app.ini file contents",
	RunE:  runConfigRawGet,
}

var configRawSetCmd = &cobra.Command{
	Use:   "raw-set",
	Short: "Replace the entire app.ini file with content read from stdin",
	Long: `Replace the entire app.ini file with content read from stdin.

A backup of the previous file is written alongside it as app.ini.bak
before the new content is applied.

Example:
  cat new-app.ini | forgejo-forge config raw-set`,
	RunE: runConfigRawSet,
}

var configEnablePushCreateCmd = &cobra.Command{
	Use:   "enable-push-create",
	Short: "Enable push-to-create for users and orgs in app.ini",
	Long: `Enable push-to-create without re-running the full 'setup' command.
Writes into [repository]:

  ENABLE_PUSH_CREATE_USER = true
  ENABLE_PUSH_CREATE_ORG  = true

Useful if you already ran setup, or if you want to enable this feature
on an existing Forgejo instance managed by forgejo-forge.`,
	RunE: runConfigEnablePushCreate,
}

var configEnableActionsCmd = &cobra.Command{
	Use:   "enable-actions",
	Short: "Enable [actions] + [actions.artifacts] with a local artifact cache path",
	Long: `Enable Forgejo Actions and local artifact storage without re-running
the full 'setup' command. Writes:

  [actions]
  ENABLED = true

  [actions.artifacts]
  STORAGE_TYPE = local
  PATH = <data-dir>/artifacts

Useful if you already ran setup, or hand-edited app.ini and only added
ENABLED/STORAGE_TYPE without a PATH (artifacts will silently fail to
appear anywhere predictable without it).`,
	RunE: runConfigEnableActions,
}

func init() {
	configCmd.AddCommand(
		configPathCmd,
		configListCmd,
		configSectionsCmd,
		configGetCmd,
		configSetCmd,
		configRemoveCmd,
		configRawGetCmd,
		configRawSetCmd,
		configEnableActionsCmd,
		configEnablePushCreateCmd,
	)
}

// resolveIniPath returns the app.ini path for the current environment.
func resolveIniPath() (string, error) {
	mode := detect.Env()
	paths, err := svc.Resolve(mode)
	if err != nil {
		return "", fmt.Errorf("resolve paths: %w", err)
	}
	return paths.IniPath, nil
}

// resolvePaths returns the full svc.Paths for the current environment.
func resolvePaths() (svc.Paths, error) {
	mode := detect.Env()
	paths, err := svc.Resolve(mode)
	if err != nil {
		return svc.Paths{}, fmt.Errorf("resolve paths: %w", err)
	}
	return paths, nil
}

func runConfigPath(_ *cobra.Command, _ []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	fmt.Println(iniPath)
	return nil
}

func runConfigSections(_ *cobra.Command, _ []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	sections, err := config.ListSections(iniPath)
	if err != nil {
		return err
	}
	for _, s := range sections {
		fmt.Println(s)
	}
	return nil
}

func runConfigList(_ *cobra.Command, args []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	pairs, err := config.ListSection(iniPath, args[0])
	if err != nil {
		return err
	}
	if len(pairs) == 0 {
		fmt.Printf("(section [%s] is empty or does not exist)\n", args[0])
		return nil
	}
	for _, kv := range pairs {
		fmt.Printf("%s = %s\n", kv.Key, kv.Value)
	}
	return nil
}

func runConfigGet(_ *cobra.Command, args []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	val, ok, err := config.GetKey(iniPath, args[0], args[1])
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("key %q not found in [%s]", args[1], args[0])
	}
	fmt.Println(val)
	return nil
}

func runConfigSet(_ *cobra.Command, args []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	section, key, value := args[0], args[1], args[2]
	if err := config.SetKey(iniPath, section, key, value); err != nil {
		return err
	}
	fmt.Printf("✔ [%s] %s = %s  (written to %s)\n", section, key, value, iniPath)
	fmt.Println("  Restart Forgejo for this change to take effect: forgejo-forge restart")
	return nil
}

func runConfigRemove(_ *cobra.Command, args []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	section, key := args[0], args[1]
	removed, err := config.RemoveKey(iniPath, section, key)
	if err != nil {
		return err
	}
	if !removed {
		fmt.Printf("⚠ %q not found in [%s] — nothing to remove\n", key, section)
		return nil
	}
	fmt.Printf("✔ Removed [%s] %s  (from %s)\n", section, key, iniPath)
	fmt.Println("  Restart Forgejo for this change to take effect: forgejo-forge restart")
	return nil
}

func runConfigEnablePushCreate(_ *cobra.Command, _ []string) error {
	paths, err := resolvePaths()
	if err != nil {
		return err
	}
	if err := config.Exists(paths.IniPath); err != nil {
		return err
	}
	if err := enablePushCreateConfig(paths.IniPath); err != nil {
		return err
	}
	fmt.Println("  Restart Forgejo for this change to take effect: forgejo-forge restart")
	return nil
}

func runConfigEnableActions(_ *cobra.Command, _ []string) error {
	paths, err := resolvePaths()
	if err != nil {
		return err
	}
	if err := config.Exists(paths.IniPath); err != nil {
		return err
	}
	if err := enableActionsConfig(paths.IniPath, paths.BaseDir); err != nil {
		return err
	}
	fmt.Println("  Restart Forgejo for this change to take effect: forgejo-forge restart")
	return nil
}

func runConfigRawGet(_ *cobra.Command, _ []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	if err := config.Exists(iniPath); err != nil {
		return err
	}
	data, err := os.ReadFile(iniPath)
	if err != nil {
		return fmt.Errorf("read %s: %w", iniPath, err)
	}
	// Write raw bytes directly to stdout — avoid fmt adding a trailing
	// newline if the file doesn't already end with one.
	_, err = os.Stdout.Write(data)
	return err
}

func runConfigRawSet(_ *cobra.Command, _ []string) error {
	iniPath, err := resolveIniPath()
	if err != nil {
		return err
	}
	if err := config.Exists(iniPath); err != nil {
		return err
	}

	newContent, err := io.ReadAll(os.Stdin)
	if err != nil {
		return fmt.Errorf("read stdin: %w", err)
	}
	if len(newContent) == 0 {
		return fmt.Errorf("refusing to write an empty app.ini (no input on stdin)")
	}

	old, err := os.ReadFile(iniPath)
	if err != nil {
		return fmt.Errorf("read %s: %w", iniPath, err)
	}
	backupPath := iniPath + ".bak"
	if err := os.WriteFile(backupPath, old, 0o640); err != nil {
		return fmt.Errorf("write backup %s: %w", backupPath, err)
	}

	if err := os.WriteFile(iniPath, newContent, 0o640); err != nil {
		return fmt.Errorf("write %s: %w", iniPath, err)
	}

	fmt.Printf("✔ app.ini updated (%d bytes)\n", len(newContent))
	fmt.Printf("  Backup saved: %s\n", backupPath)
	fmt.Println("  Restart Forgejo for this change to take effect: forgejo-forge restart")
	return nil
}
