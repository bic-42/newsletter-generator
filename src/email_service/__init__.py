"""
Email service package for the newsletter generation system.
Contains modules for managing subscribers and sending emails.
"""

from .email_sender import EmailSender
from .subscriber_manager import SubscriberManager

__all__ = ['EmailSender', 'SubscriberManager']