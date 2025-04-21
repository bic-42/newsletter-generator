"""
Configuration module for the newsletter generation system.
Loads environment variables from .env file and provides access to configuration settings.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Import logger from config directory
from config.logger import logger

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Financial Data API Keys
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
FRED_API_KEY = os.getenv('FRED_API_KEY')

# Email Configuration
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_SENDER_NAME = os.getenv('EMAIL_SENDER_NAME', 'Financial Newsletter')

# Newsletter Configuration
NEWSLETTER_TITLE = os.getenv('NEWSLETTER_TITLE', 'Weekly Financial Insights')
NEWSLETTER_FREQUENCY = os.getenv('NEWSLETTER_FREQUENCY', 'weekly')
NEWSLETTER_SEND_DAY = os.getenv('NEWSLETTER_SEND_DAY', 'monday').lower()
NEWSLETTER_SEND_TIME = os.getenv('NEWSLETTER_SEND_TIME', '08:00')
