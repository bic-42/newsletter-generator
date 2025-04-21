"""
Main script for the newsletter generation system.

This script orchestrates the entire workflow:
1. Fetches financial data from various sources
2. Generates a newsletter using language models
3. Distributes the newsletter to subscribers
4. Schedules the process to run weekly
"""

import os
import time
import schedule
from datetime import datetime
from pathlib import Path
import argparse

from src.config import NEWSLETTER_SEND_DAY, NEWSLETTER_SEND_TIME
from config.logger import logger
from src.data_sources import StockMarketData, EconomicIndicators, NewsHeadlines
from src.newsletter_generator import NewsletterGenerator
from src.email_service import EmailSender, SubscriberManager

# Initialize logger
logger = logger.getChild(__name__)

def generate_and_send_newsletter(test_mode=False, save_only=False, test_recipients=None):
    """
    Generate and send the newsletter.

    Args:
        test_mode: If True, send only to test recipients
        save_only: If True, only save the newsletter to file without sending
        test_recipients: List of email addresses to send to in test mode

    Returns:
        True if successful, False otherwise
    """
    start_time = time.time()
    logger.info("Starting newsletter generation and distribution process")

    try:
        # Initialize newsletter generator
        newsletter_generator = NewsletterGenerator()

        # Generate newsletter
        logger.info("Generating newsletter")
        newsletter = newsletter_generator.generate_newsletter()

        if not newsletter:
            logger.error("Failed to generate newsletter")
            return False

        # Initialize email sender
        email_sender = EmailSender()

        # Save newsletter to file
        output_dir = Path(__file__).parent / 'newsletters'
        newsletter_path = email_sender.save_newsletter_to_file(newsletter, output_dir)

        if not newsletter_path:
            logger.error("Failed to save newsletter to file")
            return False

        logger.info(f"Newsletter saved to {newsletter_path}")

        # Send newsletter if not in save-only mode
        if not save_only:
            logger.info("Sending newsletter to subscribers")
            success = email_sender.send_newsletter(
                newsletter, 
                test_mode=test_mode,
                test_recipients=test_recipients
            )

            if not success:
                logger.error("Failed to send newsletter")
                return False

            logger.info("Newsletter sent successfully")

        elapsed_time = time.time() - start_time
        logger.info(f"Newsletter process completed in {elapsed_time:.2f} seconds")
        return True

    except Exception as e:
        logger.error(f"Error in newsletter process: {str(e)}")
        return False

def add_subscriber(email, name=None):
    """
    Add a subscriber to the newsletter.

    Args:
        email: Subscriber's email address
        name: Subscriber's name (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        subscriber_manager = SubscriberManager()
        success = subscriber_manager.add_subscriber(email, name)

        if success:
            logger.info(f"Added subscriber: {email}")
        else:
            logger.error(f"Failed to add subscriber: {email}")

        return success

    except Exception as e:
        logger.error(f"Error adding subscriber: {str(e)}")
        return False

def remove_subscriber(email):
    """
    Remove a subscriber from the newsletter.

    Args:
        email: Subscriber's email address

    Returns:
        True if successful, False otherwise
    """
    try:
        subscriber_manager = SubscriberManager()
        success = subscriber_manager.remove_subscriber(email)

        if success:
            logger.info(f"Removed subscriber: {email}")
        else:
            logger.error(f"Failed to remove subscriber: {email}")

        return success

    except Exception as e:
        logger.error(f"Error removing subscriber: {str(e)}")
        return False

def list_subscribers():
    """
    List all subscribers.

    Returns:
        List of subscriber dictionaries
    """
    try:
        subscriber_manager = SubscriberManager()
        subscribers = subscriber_manager.get_all_subscribers()

        logger.info(f"Found {len(subscribers)} subscribers")
        return subscribers

    except Exception as e:
        logger.error(f"Error listing subscribers: {str(e)}")
        return []

def schedule_newsletter():
    """
    Schedule the newsletter to run weekly.
    """
    # Get day and time from config
    day = NEWSLETTER_SEND_DAY.lower() or "monday"
    time_str = NEWSLETTER_SEND_TIME or "08:00"

    # Schedule based on day
    if day == "monday":
        schedule.every().monday.at(time_str).do(generate_and_send_newsletter)
    elif day == "tuesday":
        schedule.every().tuesday.at(time_str).do(generate_and_send_newsletter)
    elif day == "wednesday":
        schedule.every().wednesday.at(time_str).do(generate_and_send_newsletter)
    elif day == "thursday":
        schedule.every().thursday.at(time_str).do(generate_and_send_newsletter)
    elif day == "friday":
        schedule.every().friday.at(time_str).do(generate_and_send_newsletter)
    elif day == "saturday":
        schedule.every().saturday.at(time_str).do(generate_and_send_newsletter)
    elif day == "sunday":
        schedule.every().sunday.at(time_str).do(generate_and_send_newsletter)
    else:
        # Default to Monday if invalid day
        schedule.every().monday.at(time_str).do(generate_and_send_newsletter)

    logger.info(f"Newsletter scheduled to run every {day.capitalize()} at {time_str}")

    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """
    Main function to parse arguments and run the appropriate command.
    """
    parser = argparse.ArgumentParser(description="Financial Newsletter Generator")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate and send newsletter")
    generate_parser.add_argument("--test", action="store_true", help="Run in test mode")
    generate_parser.add_argument("--save-only", action="store_true", help="Only save newsletter without sending")
    generate_parser.add_argument("--recipients", nargs="+", help="Test recipients (only used with --test)")

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Schedule newsletter to run weekly")

    # Subscriber management commands
    add_parser = subparsers.add_parser("add", help="Add a subscriber")
    add_parser.add_argument("email", help="Subscriber's email address")
    add_parser.add_argument("--name", help="Subscriber's name")

    remove_parser = subparsers.add_parser("remove", help="Remove a subscriber")
    remove_parser.add_argument("email", help="Subscriber's email address")

    list_parser = subparsers.add_parser("list", help="List all subscribers")

    # Parse arguments
    args = parser.parse_args()

    # Run the appropriate command
    if args.command == "generate":
        generate_and_send_newsletter(
            test_mode=args.test,
            save_only=args.save_only,
            test_recipients=args.recipients
        )
    elif args.command == "schedule":
        schedule_newsletter()
    elif args.command == "add":
        add_subscriber(args.email, args.name)
    elif args.command == "remove":
        remove_subscriber(args.email)
    elif args.command == "list":
        subscribers = list_subscribers()
        print(f"Total subscribers: {len(subscribers)}")
        for s in subscribers:
            status = "active" if s.get("active", True) else "inactive"
            print(f"{s.get('email')} - {s.get('name', 'N/A')} - {status}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
