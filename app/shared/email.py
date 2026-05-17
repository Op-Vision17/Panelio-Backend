import logging
from email.message import EmailMessage

from aiosmtplib import send

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_email(to: str, otp: str):
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(f"SMTP credentials not set. OTP for {to} is: {otp}")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    message["To"] = to
    message["Subject"] = "Your Panelio OTP"
    message.set_content(
        f"Your Panelio OTP is: {otp}\n\nThis OTP is valid for 5 minutes. If you did not request this, please ignore this email."
    )

    try:
        await send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_PORT == 465,
            start_tls=settings.SMTP_PORT == 587,
        )
        logger.info(f"OTP email sent to {to}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        # In development, we still want to see the OTP
        logger.info(f"DEV LOG: OTP for {to} is {otp}")
