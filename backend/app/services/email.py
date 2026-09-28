import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings

logger = logging.getLogger('verifact.email')
settings = get_settings()


def _send_email(recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_configured:
        raise RuntimeError('SMTP is not configured. Set VERIFACT_SMTP_HOST and VERIFACT_SMTP_FROM_EMAIL.')
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = f'{settings.smtp_from_name} <{settings.smtp_from_email}>'
    message['To'] = recipient
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.ehlo()
        if settings.smtp_starttls:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or '')
        smtp.send_message(message)


def send_password_reset_email(recipient: str, reset_token: str) -> None:
    reset_url = f"{settings.public_base_url.rstrip('/')}/reset?token={quote(reset_token)}"
    _send_email(
        recipient,
        'Reset your VeriFact password',
        'VeriFact — Verify. Understand. Trust.\n\n'
        'A password reset was requested for your VeriFact account. Open this link to set a new password:\n\n'
        f'{reset_url}\n\n'
        'This link expires in 30 minutes and can be used once. If you did not request it, you can ignore this email.',
    )


def send_email_verification_email(recipient: str, verification_token: str) -> None:
    verify_url = f"{settings.public_base_url.rstrip('/')}/verify-email?token={quote(verification_token)}"
    _send_email(
        recipient,
        'Verify your VeriFact email address',
        'Welcome to VeriFact — Verify. Understand. Trust.\n\n'
        'Please verify your email address to activate your account:\n\n'
        f'{verify_url}\n\n'
        'This link expires in 24 hours and can be used once. If you did not create this account, you can ignore this email.',
    )
