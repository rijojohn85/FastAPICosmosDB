from app.core.config.settings import Settings
from app.services.gmail_sender import GmailSender
from app.services.logging_service import logger
def send_email(
        subject: str,
        body: str,
        settings: Settings
) -> None:
    """
    Send email notification using Gmail API.
    Args:
        subject: Email subject
        body: Email body
        settings: Application configuration with email details
    """
    try:
        with GmailSender(settings) as email_sender:
            email_sender.send(
                to=settings.GMAIL_ADDRESS,
                subject=subject,
                body=body,
            )
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}")
