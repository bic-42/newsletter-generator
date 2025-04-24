"""
Configuration module for the newsletter generation system.
Loads environment variables from .env file and provides access to configuration settings.
"""

import os
from dotenv import load_dotenv
from pathlib import Path





# Load environment variables from .env file
# env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if OPENAI_API_KEY:
  print(f"Successfully loaded API Key: {OPENAI_API_KEY[:4]}...{OPENAI_API_KEY[-4:]}") # Print partial key for security
else:
  print("API_KEY not found. Make sure it's set in your .env file and load_dotenv() was called.")

# Financial Data API Keys
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
FRED_API_KEY = os.getenv('FRED_API_KEY')
CMC_PRO_API_KEY = os.getenv('CMC_PRO_API_KEY')
COINGECKO_API_KEY = os.getenv('demo_api_key')

# Email Configuration
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_SENDER_NAME = os.getenv('EMAIL_SENDER_NAME', 'Financial Newsletter')

# Newsletter Configuration
NEWSLETTER_TITLE = os.getenv('NEWSLETTER_TITLE', 'Weekly Financial Insights')
NEWSLETTER_FREQUENCY = os.getenv('NEWSLETTER_FREQUENCY', 'weekly')
NEWSLETTER_SEND_DAY = os.getenv('NEWSLETTER_SEND_DAY', 'monday').lower()
NEWSLETTER_SEND_TIME = os.getenv('NEWSLETTER_SEND_TIME', '08:00')
