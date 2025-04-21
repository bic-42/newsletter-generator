"""
Configuration module for the newsletter generation system.
Loads environment variables from .env file and provides access to configuration settings.
"""

import os
import logging
from dotenv import load_dotenv
from pathlib import Path

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

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = Path(__file__).parent.parent / 'logs'

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
def setup_logging():
    """Set up logging configuration."""
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    log_file = LOG_DIR / 'newsletter_generator.log'
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Check for missing critical configuration
    if not OPENAI_API_KEY:
        logging.warning("OpenAI API key is missing. Newsletter generation may fail.")
    
    if not SENDGRID_API_KEY or not EMAIL_SENDER:
        logging.warning("Email configuration is incomplete. Newsletter distribution may fail.")
    
    return logging.getLogger('newsletter_generator')

# Create logger instance
logger = setup_logging()