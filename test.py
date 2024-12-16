import smtplib
from email.mime.text import MIMEText

smtp_host = 'mail.dpl.org.np'
smtp_port = 587
smtp_user = 'no-reply@dpl.org.np'
smtp_password = 'Noreply@1221'

msg = MIMEText('This is a test email.')
msg['Subject'] = 'Test Email'
msg['From'] = smtp_user
msg['To'] = 'meet.upretybnd@gmail.com'

try:
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()  # Start TLS encryption
        server.login(smtp_user, smtp_password)  # Log in with your credentials
        server.sendmail(smtp_user, 'meet.upretybnd@gmail.com', msg.as_string())  # Send email
    print("Test email sent successfully.")
except smtplib.SMTPAuthenticationError as e:
    print(f"SMTP Authentication failed: {e}")
