import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings

logger = logging.getLogger('verifact.email')
settings = get_settings()


def send_password_reset_email(recipient: str, reset_token: str) -> None:
    """Send a branded reset message only when production SMTP is configured."""
    if not settings.smtp_configured:
        logger.warning('Password reset requested without production SMTP configuration')
        return
    reset_url = f"{settings.public_base_url.rstrip('/')}/reset?token={quote(reset_token)}"
    message = EmailMessage()
    message['Subject'] = 'Reset your VeriFact password'
    message['From'] = f'{settings.smtp_from_name} <{settings.smtp_from_email}>'
    message['To'] = recipient
    message.set_content(
        'VeriFact — Verify. Understand. Trust.\n\n'
        'A password reset was requested for your VeriFact account. Open this link to set a new password:\n\n'
        f'{reset_url}\n\n'
        'This link expires in 30 minutes and can be used once. If you did not request it, you can ignore this email.'
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or '')
        smtp.send_message(message)
