import smtplib
import os
from email.mime.text import MIMEText

smtp_host = os.getenv("SMTP_HOST", "mail.dpl.org.np")
smtp_port = int(os.getenv("SMTP_PORT", "587"))
smtp_user = os.getenv("SMTP_USER", "no-reply@dpl.org.np")
smtp_password = os.getenv("SMTP_PASSWORD", "")

msg = MIMEText('This is a test email.')
msg['Subject'] = 'Test Email'
msg['From'] = smtp_user
msg['To'] = 'meet.upretybnd@gmail.com'

if __name__ == "__main__":
    if not smtp_password:
        raise SystemExit("Set SMTP_PASSWORD to run this script.")
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, "meet.upretybnd@gmail.com", msg.as_string())
        print("Test email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication failed: {e}")
