"""
Logging configuration for the newsletter generation system.
Sets up logging with file and console output.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = Path(__file__).parent.parent / 'logs'

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

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
    openai_api_key = os.getenv('OPENAI_API_KEY')
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
    email_sender = os.getenv('EMAIL_SENDER')
    
    if not openai_api_key:
        logging.warning("OpenAI API key is missing. Newsletter generation may fail.")
    
    if not sendgrid_api_key or not email_sender:
        logging.warning("Email configuration is incomplete. Newsletter distribution may fail.")
    
    return logging.getLogger('newsletter_generator')

# Create logger instance
logger = setup_logging()