package cmd

import (
	"fmt"

	"github.com/dev-boffin-io/forgejo-forge/internal/config"
	"github.com/dev-boffin-io/forgejo-forge/internal/detect"
	"github.com/dev-boffin-io/forgejo-forge/internal/svc"
	"github.com/spf13/cobra"
)

var (
	flagMailFrom     string
	flagMailProto    string
	flagMailSMTPAddr string
	flagMailSMTPPort int
	flagMailUser     string
	flagMailPasswd   string
)

var emailCmd = &cobra.Command{
	Use:   "email-setup",
	Short: "Configure [mailer] section in app.ini for SMTP/SMTPS email",
	Long: `Patches (or appends) the [mailer] section in the active app.ini.

Examples:
  # Gmail with App Password (smtps / port 465)
  forgejo-forge email-setup \
    --from   forgejo@yourdomain.com \
    --user   yourname@gmail.com \
    --passwd "xxxx xxxx xxxx xxxx" \
    --smtp-addr smtp.gmail.com \
    --smtp-port 465 --protocol smtps

  # Brevo / Mailgun STARTTLS (port 587)
  forgejo-forge email-setup \
    --from   forgejo@yourdomain.com \
    --user   apikey \
    --passwd "your-api-key" \
    --smtp-addr smtp-relay.brevo.com \
    --smtp-port 587 --protocol smtp

After running this command, restart Forgejo:
  forgejo-forge restart

Then test via Admin Panel → Site Administration → Configuration → SMTP Mailer.`,
	RunE: runEmailSetup,
}

func init() {
	emailCmd.Flags().StringVar(&flagMailFrom, "from", "",
		"Sender address shown in outgoing mail, e.g. forgejo@yourdomain.com  [required]")
	emailCmd.Flags().StringVar(&flagMailProto, "protocol", "smtps",
		`SMTP protocol: "smtps" (SSL/TLS, port 465) or "smtp" (STARTTLS, port 587)`)
	emailCmd.Flags().StringVar(&flagMailSMTPAddr, "smtp-addr", "smtp.gmail.com",
		"SMTP server hostname")
	emailCmd.Flags().IntVar(&flagMailSMTPPort, "smtp-port", 465,
		"SMTP port — 465 for smtps, 587 for smtp/STARTTLS")
	emailCmd.Flags().StringVar(&flagMailUser, "user", "",
		"SMTP login username (usually your email address)  [required]")
	emailCmd.Flags().StringVar(&flagMailPasswd, "passwd", "",
		"SMTP password or App Password (use App Password when Gmail 2FA is on)  [required]")

	_ = emailCmd.MarkFlagRequired("from")
	_ = emailCmd.MarkFlagRequired("user")
	_ = emailCmd.MarkFlagRequired("passwd")
}

func runEmailSetup(_ *cobra.Command, _ []string) error {
	mode := detect.Env()
	paths, err := svc.Resolve(mode)
	if err != nil {
		return err
	}
	if err := config.Exists(paths.IniPath); err != nil {
		return err
	}

	p := config.MailerParams{
		Enabled:  true,
		From:     flagMailFrom,
		Protocol: flagMailProto,
		SMTPAddr: flagMailSMTPAddr,
		SMTPPort: flagMailSMTPPort,
		User:     flagMailUser,
		Passwd:   flagMailPasswd,
	}

	if err := config.WriteMailer(paths.IniPath, p); err != nil {
		return fmt.Errorf("write mailer config: %w", err)
	}

	fmt.Printf("✔ [mailer] section written → %s\n", paths.IniPath)
	fmt.Println("▶ Restart Forgejo to apply:  forgejo-forge restart")
	fmt.Println("📧 Then test: Admin Panel → Site Administration → Configuration → SMTP Mailer")
	return nil
}
