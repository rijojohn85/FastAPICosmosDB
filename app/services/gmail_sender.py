from typing import Optional, Dict, Any
import smtplib
from email.message import EmailMessage
from app.core.config.settings import Settings, get_settings

class GmailSender:
    """
    Secure Gmail sender with TLS and type-safe config
    Example usage:
    with GmailSender(settings) as sender:
        sender.send(
        to="user@company.com",
        subject="Test email",
        body="This is a test email"
        )
    """
    def __init__(self, settings: Settings)-> None:
        self.settings = settings
        self.connection: Optional[smtplib.SMTP] = None

    def __enter__(self) -> "GmailSender":
        """Context manager entry with TLS Handshake"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) ->None:
        """Context manager exit with proper cleanup"""
        self.disconnect()
    def connect(self)->None:
        """Connect to Gmail SMTP server with TLS"""
        self.connection = smtplib.SMTP("smtp.gmail.com", 587)
        self.connection.ehlo()
        self.connection.starttls()
        self.connection.login(
            self.settings.GMAIL_ADDRESS,
            self.settings.GMAIL_PASSWORD
        )
    def disconnect(self)->None:
        """Disconnect from Gmail SMTP server"""
        if self.connection:
            self.connection.quit()
            self.connection = None

    def send(self, to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str]=None)->Dict[str, Any]:
        """
        Send an email using Gmail SMTP server
        Args:
            to (str): recipient email address
            subject (str): email subject
            body (str): email body
        Returns:
            Dictionary with send operation results
        Raises:
            ValueError: for invalid email address
            SMTPException: for SMTP server errors
        """
        if not self.connection:
            raise RuntimeError("Not connected to SMTP server")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.GMAIL_ADDRESS
        message["To"] = to
        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc
        message.set_content(body)
        try:
            self.connection.send_message(message)
            return {
                "success": True,
                "message_id" : message["Message-ID"],
                "recipients": [to]+ ([cc] if cc else []) + ([bcc] if bcc else [])
            }
        except smtplib.SMTPException as e:
            return {
                "success": False,
                "error": str(e)
            }
