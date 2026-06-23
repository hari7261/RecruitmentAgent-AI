import os
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv

load_dotenv()

sender = os.getenv("EMAIL_SENDER")
password = os.getenv("EMAIL_PASSKEY")
if not sender or not password:
    print("EMAIL_SENDER or EMAIL_PASSKEY not set in environment/.env")
    raise SystemExit(1)

msg = MIMEText("This is a test email from requrinmentAI.")
msg["Subject"] = "Test email"
msg["From"] = sender
msg["To"] = sender

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.set_debuglevel(1)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [sender], msg.as_string())
    print("Email sent OK")
except smtplib.SMTPAuthenticationError as e:
    print("SMTPAuthenticationError:", e)
    raise
except Exception as e:
    print("Error sending email:", e)
    raise
