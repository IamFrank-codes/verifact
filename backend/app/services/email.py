import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings

logger = logging.getLogger('verifact.email')
settings = get_settings()


def _send_email(recipient: str, subject: str, body: str, attachment: tuple[str, bytes, str] | None = None) -> None:
    if not settings.smtp_configured:
        raise RuntimeError('SMTP is not configured. Set VERIFACT_SMTP_HOST and VERIFACT_SMTP_FROM_EMAIL.')
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = f'{settings.smtp_from_name} <{settings.smtp_from_email}>'
    message['To'] = recipient
    message.set_content(body)
    if attachment:
        filename, content, content_type = attachment
        maintype, _, subtype = content_type.partition('/')
        if not maintype or not subtype:
            raise ValueError('Attachment content type must be a MIME type.')
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
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
        'If you prefer to enter the reset code manually, use this one-time code on the password reset screen:\n\n'
        f'{reset_token}\n\n'
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


def send_verification_pdf_email(recipient: str, verification_id: str, pdf_bytes: bytes) -> None:
    _send_email(
        recipient,
        'Your VeriFact verification report',
        'Attached is your requested VeriFact verification report in PDF format. Scores are conditional on retrieved evidence and policy eligibility.',
        (f'verifact-report-{verification_id[:8]}.pdf', pdf_bytes, 'application/pdf'),
    )
