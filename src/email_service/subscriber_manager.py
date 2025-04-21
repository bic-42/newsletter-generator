"""
Module for managing newsletter subscribers.
"""

import os
import json
import csv
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..config import logger

class SubscriberManager:
    """
    Manager for newsletter subscribers.
    
    Handles adding, removing, and listing subscribers.
    """
    
    def __init__(self, subscribers_file: Optional[str] = None):
        """
        Initialize the subscriber manager.
        
        Args:
            subscribers_file: Path to the subscribers file (CSV or JSON)
                             If None, defaults to 'subscribers.json' in the config directory
        """
        self.logger = logger
        
        # Set default subscribers file if none provided
        if subscribers_file is None:
            config_dir = Path(__file__).parent.parent.parent / 'config'
            self.subscribers_file = config_dir / 'subscribers.json'
        else:
            self.subscribers_file = Path(subscribers_file)
        
        # Create subscribers file if it doesn't exist
        if not self.subscribers_file.exists():
            self._create_empty_subscribers_file()
        
        # Load subscribers
        self.subscribers = self._load_subscribers()
    
    def _create_empty_subscribers_file(self):
        """Create an empty subscribers file."""
        try:
            # Create parent directory if it doesn't exist
            self.subscribers_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create empty subscribers file based on file extension
            if self.subscribers_file.suffix.lower() == '.json':
                with open(self.subscribers_file, 'w') as f:
                    json.dump([], f)
            elif self.subscribers_file.suffix.lower() == '.csv':
                with open(self.subscribers_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['email', 'name', 'active'])
            else:
                # Default to JSON
                self.subscribers_file = self.subscribers_file.with_suffix('.json')
                with open(self.subscribers_file, 'w') as f:
                    json.dump([], f)
            
            self.logger.info(f"Created empty subscribers file: {self.subscribers_file}")
        except Exception as e:
            self.logger.error(f"Error creating subscribers file: {str(e)}")
            # Create in-memory subscribers list
            self.subscribers = []
    
    def _load_subscribers(self) -> List[Dict[str, Any]]:
        """
        Load subscribers from file.
        
        Returns:
            List of subscriber dictionaries
        """
        try:
            if not self.subscribers_file.exists():
                self.logger.warning(f"Subscribers file not found: {self.subscribers_file}")
                return []
            
            # Load based on file extension
            if self.subscribers_file.suffix.lower() == '.json':
                with open(self.subscribers_file, 'r') as f:
                    subscribers = json.load(f)
            elif self.subscribers_file.suffix.lower() == '.csv':
                subscribers = []
                with open(self.subscribers_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Convert 'active' string to boolean
                        if 'active' in row:
                            row['active'] = row['active'].lower() in ('true', 'yes', '1')
                        subscribers.append(row)
            else:
                self.logger.error(f"Unsupported file format: {self.subscribers_file.suffix}")
                return []
            
            self.logger.info(f"Loaded {len(subscribers)} subscribers from {self.subscribers_file}")
            return subscribers
            
        except Exception as e:
            self.logger.error(f"Error loading subscribers: {str(e)}")
            return []
    
    def _save_subscribers(self):
        """Save subscribers to file."""
        try:
            # Save based on file extension
            if self.subscribers_file.suffix.lower() == '.json':
                with open(self.subscribers_file, 'w') as f:
                    json.dump(self.subscribers, f, indent=2)
            elif self.subscribers_file.suffix.lower() == '.csv':
                with open(self.subscribers_file, 'w', newline='') as f:
                    if self.subscribers:
                        writer = csv.DictWriter(f, fieldnames=self.subscribers[0].keys())
                        writer.writeheader()
                        writer.writerows(self.subscribers)
                    else:
                        writer = csv.writer(f)
                        writer.writerow(['email', 'name', 'active'])
            else:
                self.logger.error(f"Unsupported file format: {self.subscribers_file.suffix}")
                return
            
            self.logger.info(f"Saved {len(self.subscribers)} subscribers to {self.subscribers_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving subscribers: {str(e)}")
    
    def add_subscriber(self, email: str, name: Optional[str] = None, active: bool = True) -> bool:
        """
        Add a new subscriber.
        
        Args:
            email: Subscriber's email address
            name: Subscriber's name (optional)
            active: Whether the subscriber is active
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if email is valid
            if not self._is_valid_email(email):
                self.logger.error(f"Invalid email address: {email}")
                return False
            
            # Check if subscriber already exists
            for subscriber in self.subscribers:
                if subscriber.get('email') == email:
                    # Update existing subscriber
                    subscriber['name'] = name if name is not None else subscriber.get('name', '')
                    subscriber['active'] = active
                    self._save_subscribers()
                    self.logger.info(f"Updated subscriber: {email}")
                    return True
            
            # Add new subscriber
            self.subscribers.append({
                'email': email,
                'name': name or '',
                'active': active
            })
            
            self._save_subscribers()
            self.logger.info(f"Added new subscriber: {email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding subscriber: {str(e)}")
            return False
    
    def remove_subscriber(self, email: str) -> bool:
        """
        Remove a subscriber.
        
        Args:
            email: Subscriber's email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find subscriber
            for i, subscriber in enumerate(self.subscribers):
                if subscriber.get('email') == email:
                    # Remove subscriber
                    del self.subscribers[i]
                    self._save_subscribers()
                    self.logger.info(f"Removed subscriber: {email}")
                    return True
            
            self.logger.warning(f"Subscriber not found: {email}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing subscriber: {str(e)}")
            return False
    
    def deactivate_subscriber(self, email: str) -> bool:
        """
        Deactivate a subscriber.
        
        Args:
            email: Subscriber's email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find subscriber
            for subscriber in self.subscribers:
                if subscriber.get('email') == email:
                    # Deactivate subscriber
                    subscriber['active'] = False
                    self._save_subscribers()
                    self.logger.info(f"Deactivated subscriber: {email}")
                    return True
            
            self.logger.warning(f"Subscriber not found: {email}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error deactivating subscriber: {str(e)}")
            return False
    
    def activate_subscriber(self, email: str) -> bool:
        """
        Activate a subscriber.
        
        Args:
            email: Subscriber's email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find subscriber
            for subscriber in self.subscribers:
                if subscriber.get('email') == email:
                    # Activate subscriber
                    subscriber['active'] = True
                    self._save_subscribers()
                    self.logger.info(f"Activated subscriber: {email}")
                    return True
            
            self.logger.warning(f"Subscriber not found: {email}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error activating subscriber: {str(e)}")
            return False
    
    def get_active_subscribers(self) -> List[Dict[str, Any]]:
        """
        Get all active subscribers.
        
        Returns:
            List of active subscriber dictionaries
        """
        return [s for s in self.subscribers if s.get('active', True)]
    
    def get_all_subscribers(self) -> List[Dict[str, Any]]:
        """
        Get all subscribers.
        
        Returns:
            List of all subscriber dictionaries
        """
        return self.subscribers
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Check if an email address is valid.
        
        Args:
            email: Email address to check
            
        Returns:
            True if valid, False otherwise
        """
        import re
        # Simple email validation regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))