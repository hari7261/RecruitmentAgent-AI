"""
Email service utilities.

Uses Python's built-in smtplib for MVP. Can be swapped for SendGrid,
Postmark, or AWS SES without changing caller code.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Send an email via SMTP.

    In production, swap this for SendGrid/Postmark/SES.
    For now, uses SMTP settings from environment variables.
    """
    smtp_host = getattr(settings, "smtp_host", None)
    smtp_port = getattr(settings, "smtp_port", 587)
    smtp_user = getattr(settings, "smtp_user", None)
    smtp_password = getattr(settings, "smtp_password", None)
    from_email = getattr(settings, "from_email", "noreply@example.com")

    if not smtp_host or not smtp_user:
        logger.warning("SMTP not configured. Email not sent to %s (subject: %s)", to_email, subject)
        logger.info("Email content:\n%s", text_body or html_body)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False
