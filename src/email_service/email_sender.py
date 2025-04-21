"""
Module for sending newsletter emails using SendGrid.
"""

import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId

from ..config import SENDGRID_API_KEY, EMAIL_SENDER, EMAIL_SENDER_NAME
from config.logger import logger
from .subscriber_manager import SubscriberManager

class EmailSender:
    """
    Sender for newsletter emails.

    Uses SendGrid to send emails to subscribers.
    """

    def __init__(self, subscriber_manager: Optional[SubscriberManager] = None):
        """
        Initialize the email sender.

        Args:
            subscriber_manager: SubscriberManager instance for managing subscribers
                               If None, a new instance will be created
        """
        self.logger = logger

        # Check for SendGrid API key
        if not SENDGRID_API_KEY:
            self.logger.error("SendGrid API key is missing. Email sending will fail.")

        # Check for sender email
        if not EMAIL_SENDER:
            self.logger.error("Sender email is missing. Email sending will fail.")

        # Set sender information
        self.sender_email = EMAIL_SENDER
        self.sender_name = EMAIL_SENDER_NAME or "Financial Newsletter"

        # Initialize subscriber manager
        self.subscriber_manager = subscriber_manager or SubscriberManager()

    def send_newsletter(self, 
                       newsletter: Dict[str, Any], 
                       test_mode: bool = False,
                       test_recipients: Optional[List[str]] = None) -> bool:
        """
        Send the newsletter to subscribers.

        Args:
            newsletter: Newsletter data from NewsletterGenerator
            test_mode: If True, send only to test recipients
            test_recipients: List of email addresses to send to in test mode

        Returns:
            True if successful, False otherwise
        """
        try:
            if not SENDGRID_API_KEY or not self.sender_email:
                self.logger.error("Missing SendGrid API key or sender email")
                return False

            # Get newsletter content
            subject = f"{newsletter.get('title', 'Financial Newsletter')} - {newsletter.get('date', '')}"
            html_content = newsletter.get('html_content', '')

            if not html_content:
                self.logger.error("Newsletter content is empty")
                return False

            # Get recipients
            if test_mode and test_recipients:
                recipients = test_recipients
                self.logger.info(f"Test mode: sending to {len(recipients)} test recipients")
            else:
                # Get active subscribers
                subscribers = self.subscriber_manager.get_active_subscribers()
                recipients = [s.get('email') for s in subscribers if s.get('email')]
                self.logger.info(f"Sending newsletter to {len(recipients)} subscribers")

            if not recipients:
                self.logger.warning("No recipients to send to")
                return False

            # Send emails in batches to avoid SendGrid limits
            batch_size = 100
            success_count = 0

            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i+batch_size]
                if self._send_batch(subject, html_content, batch):
                    success_count += len(batch)

            self.logger.info(f"Successfully sent newsletter to {success_count}/{len(recipients)} recipients")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"Error sending newsletter: {str(e)}")
            return False

    def _send_batch(self, subject: str, html_content: str, recipients: List[str]) -> bool:
        """
        Send a batch of emails.

        Args:
            subject: Email subject
            html_content: HTML content of the email
            recipients: List of recipient email addresses

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create SendGrid message
            message = Mail(
                from_email=self.sender_email,
                to_emails=recipients,
                subject=subject,
                html_content=html_content
            )

            # Set sender name
            message.from_email = (self.sender_email, self.sender_name)

            # Use BCC for multiple recipients
            if len(recipients) > 1:
                message.to_emails = self.sender_email  # Set primary recipient to sender
                message.add_bcc(recipients)  # Add actual recipients as BCC

            # Send the message
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)

            # Check response
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(f"Successfully sent batch of {len(recipients)} emails")
                return True
            else:
                self.logger.error(f"Error sending batch: {response.status_code} - {response.body}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending batch: {str(e)}")
            return False

    def send_newsletter_with_attachment(self, 
                                       newsletter: Dict[str, Any], 
                                       attachment_path: str,
                                       test_mode: bool = False,
                                       test_recipients: Optional[List[str]] = None) -> bool:
        """
        Send the newsletter with an attachment.

        Args:
            newsletter: Newsletter data from NewsletterGenerator
            attachment_path: Path to the attachment file
            test_mode: If True, send only to test recipients
            test_recipients: List of email addresses to send to in test mode

        Returns:
            True if successful, False otherwise
        """
        try:
            if not SENDGRID_API_KEY or not self.sender_email:
                self.logger.error("Missing SendGrid API key or sender email")
                return False

            # Check if attachment exists
            attachment_path = Path(attachment_path)
            if not attachment_path.exists():
                self.logger.error(f"Attachment not found: {attachment_path}")
                return False

            # Get newsletter content
            subject = f"{newsletter.get('title', 'Financial Newsletter')} - {newsletter.get('date', '')}"
            html_content = newsletter.get('html_content', '')

            if not html_content:
                self.logger.error("Newsletter content is empty")
                return False

            # Get recipients
            if test_mode and test_recipients:
                recipients = test_recipients
                self.logger.info(f"Test mode: sending to {len(recipients)} test recipients")
            else:
                # Get active subscribers
                subscribers = self.subscriber_manager.get_active_subscribers()
                recipients = [s.get('email') for s in subscribers if s.get('email')]
                self.logger.info(f"Sending newsletter to {len(recipients)} subscribers")

            if not recipients:
                self.logger.warning("No recipients to send to")
                return False

            # Read attachment
            with open(attachment_path, 'rb') as f:
                attachment_content = base64.b64encode(f.read()).decode()

            # Get file type
            file_type = self._get_file_type(attachment_path.suffix)

            # Create attachment
            attachment = Attachment()
            attachment.file_content = FileContent(attachment_content)
            attachment.file_name = FileName(attachment_path.name)
            attachment.file_type = FileType(file_type)
            attachment.disposition = Disposition('attachment')
            attachment.content_id = ContentId('newsletter_attachment')

            # Send emails in batches to avoid SendGrid limits
            batch_size = 100
            success_count = 0

            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i+batch_size]
                if self._send_batch_with_attachment(subject, html_content, batch, attachment):
                    success_count += len(batch)

            self.logger.info(f"Successfully sent newsletter with attachment to {success_count}/{len(recipients)} recipients")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"Error sending newsletter with attachment: {str(e)}")
            return False

    def _send_batch_with_attachment(self, subject: str, html_content: str, recipients: List[str], attachment: Attachment) -> bool:
        """
        Send a batch of emails with an attachment.

        Args:
            subject: Email subject
            html_content: HTML content of the email
            recipients: List of recipient email addresses
            attachment: SendGrid Attachment object

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create SendGrid message
            message = Mail(
                from_email=self.sender_email,
                to_emails=recipients,
                subject=subject,
                html_content=html_content
            )

            # Set sender name
            message.from_email = (self.sender_email, self.sender_name)

            # Use BCC for multiple recipients
            if len(recipients) > 1:
                message.to_emails = self.sender_email  # Set primary recipient to sender
                message.add_bcc(recipients)  # Add actual recipients as BCC

            # Add attachment
            message.add_attachment(attachment)

            # Send the message
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)

            # Check response
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(f"Successfully sent batch of {len(recipients)} emails with attachment")
                return True
            else:
                self.logger.error(f"Error sending batch with attachment: {response.status_code} - {response.body}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending batch with attachment: {str(e)}")
            return False

    def _get_file_type(self, extension: str) -> str:
        """
        Get MIME type for a file extension.

        Args:
            extension: File extension (with or without dot)

        Returns:
            MIME type string
        """
        # Remove dot if present
        if extension.startswith('.'):
            extension = extension[1:]

        # Map of common extensions to MIME types
        mime_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'html': 'text/html',
            'htm': 'text/html',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'zip': 'application/zip',
            'json': 'application/json'
        }

        return mime_types.get(extension.lower(), 'application/octet-stream')

    def save_newsletter_to_file(self, newsletter: Dict[str, Any], output_dir: Optional[str] = None) -> Optional[str]:
        """
        Save the newsletter to a file.

        Args:
            newsletter: Newsletter data from NewsletterGenerator
            output_dir: Directory to save the file (defaults to 'newsletters' in project root)

        Returns:
            Path to the saved file, or None if failed
        """
        try:
            # Set default output directory if none provided
            if output_dir is None:
                output_dir = Path(__file__).parent.parent.parent / 'newsletters'
            else:
                output_dir = Path(output_dir)

            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get newsletter content
            title = newsletter.get('title', 'Financial_Newsletter').replace(' ', '_')
            date = newsletter.get('date', '')
            html_content = newsletter.get('html_content', '')
            markdown_content = newsletter.get('content', '')

            if not html_content and not markdown_content:
                self.logger.error("Newsletter content is empty")
                return None

            # Create filename
            filename = f"{title}_{date}.html"
            file_path = output_dir / filename

            # Save HTML content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Also save markdown version if available
            if markdown_content:
                md_file_path = output_dir / f"{title}_{date}.md"
                with open(md_file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

            self.logger.info(f"Saved newsletter to {file_path}")
            return str(file_path)

        except Exception as e:
            self.logger.error(f"Error saving newsletter to file: {str(e)}")
            return None
