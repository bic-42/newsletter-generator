"""
Base class for data sources used in the newsletter generation system.
"""

from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional, Union

# Import the logger from config
from config.logger import logger

class DataSource(ABC):
    """
    Abstract base class for all data sources.

    All data sources should inherit from this class and implement the fetch_data method.
    """

    def __init__(self, name: str):
        """
        Initialize the data source.

        Args:
            name: A descriptive name for the data source
        """
        self.name = name
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """
        Fetch data from the source.

        Args:
            **kwargs: Additional parameters specific to the data source

        Returns:
            A dictionary containing the fetched data
        """
        pass

    def get_date_range(self, days: int = 7) -> tuple:
        """
        Get a date range for the data query.

        Args:
            days: Number of days to look back

        Returns:
            A tuple of (start_date, end_date) as datetime objects
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date

    def format_data_for_report(self, data: Dict[str, Any]) -> str:
        """
        Format the data for inclusion in the newsletter.

        Args:
            data: The data to format

        Returns:
            A formatted string representation of the data
        """
        # Default implementation - subclasses should override this
        return str(data)

    def log_fetch_attempt(self, **kwargs):
        """
        Log an attempt to fetch data.

        Args:
            **kwargs: Parameters used for the fetch attempt
        """
        self.logger.info(f"Fetching data from {self.name} with parameters: {kwargs}")

    def log_fetch_success(self, data_size: int):
        """
        Log a successful data fetch.

        Args:
            data_size: Size or count of the fetched data
        """
        self.logger.info(f"Successfully fetched {data_size} items from {self.name}")

    def log_fetch_error(self, error: Exception):
        """
        Log an error during data fetch.

        Args:
            error: The exception that occurred
        """
        self.logger.error(f"Error fetching data from {self.name}: {str(error)}")
