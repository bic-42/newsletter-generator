"""
Module for fetching economic indicators data from Alpha Vantage and FRED.
"""

import requests
import pandas as pd
import pandas_datareader.data as web
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import json

from .base import DataSource
from ..config import ALPHA_VANTAGE_API_KEY, FRED_API_KEY
from config.logger import logger

class EconomicIndicators(DataSource):
    """
    Data source for economic indicators.

    Fetches data about GDP, inflation, unemployment, interest rates, etc.
    """

    def __init__(self):
        """Initialize the economic indicators data source."""
        super().__init__(name="Economic Indicators")

        # Alpha Vantage API base URL
        self.alpha_vantage_url = "https://www.alphavantage.co/query"

        # Default FRED indicators to track
        self.default_fred_indicators = {
            "GDP": "GDP",                  # Gross Domestic Product
            "UNRATE": "Unemployment Rate", # Unemployment Rate
            "CPIAUCSL": "CPI",             # Consumer Price Index (Inflation)
            "FEDFUNDS": "Fed Funds Rate",  # Federal Funds Rate
            "T10Y2Y": "Yield Curve",       # 10-Year Treasury Constant Maturity Minus 2-Year
            "PAYEMS": "Nonfarm Payrolls",  # Total Nonfarm Payrolls
            "HOUST": "Housing Starts",     # Housing Starts
            "RSAFS": "Retail Sales",       # Retail Sales
            "INDPRO": "Industrial Production", # Industrial Production Index
            "M2": "M2 Money Supply"        # M2 Money Supply
        }

        self.logger = logger.getChild(self.__class__.__name__)

    def fetch_data(self, 
                  fred_indicators: Optional[Dict[str, str]] = None,
                  days: int = 365) -> Dict[str, Any]:
        """
        Fetch economic indicator data.

        Args:
            fred_indicators: Dictionary mapping FRED indicator codes to their names
                            (defaults to self.default_fred_indicators)
            days: Number of days of historical data to fetch

        Returns:
            Dictionary containing economic indicator data
        """
        self.log_fetch_attempt(fred_indicators=fred_indicators, days=days)

        try:
            # Use default indicators if none provided
            fred_indicators = fred_indicators or self.default_fred_indicators

            # Get date range
            start_date, end_date = self.get_date_range(days)

            # Fetch FRED data
            fred_data = self._fetch_fred_data(fred_indicators, start_date, end_date)

            # Fetch Alpha Vantage economic data
            alpha_vantage_data = self._fetch_alpha_vantage_data()

            # Calculate economic summary
            economic_summary = self._calculate_economic_summary(fred_data, alpha_vantage_data)

            # Prepare result
            result = {
                "economic_summary": economic_summary,
                "raw_data": {
                    "fred": fred_data,
                    "alpha_vantage": alpha_vantage_data
                }
            }

            self.log_fetch_success(len(fred_data) + len(alpha_vantage_data))
            return result

        except Exception as e:
            self.log_fetch_error(e)
            # Return empty data with error information
            return {
                "error": str(e),
                "economic_summary": {},
                "raw_data": {"fred": {}, "alpha_vantage": {}}
            }

    def _fetch_fred_data(self, indicators: Dict[str, str], start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """
        Fetch data from FRED for a list of indicator codes.

        Args:
            indicators: Dictionary mapping indicator codes to their names
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            Dictionary mapping indicator codes to their data
        """
        result = {}

        if not FRED_API_KEY:
            self.logger.warning("FRED API key is missing. Using pandas_datareader without API key.")

        for code in indicators.keys():
            try:
                # Fetch data from FRED using pandas_datareader
                data = web.DataReader(code, 'fred', start_date, end_date)

                if not data.empty:
                    result[code] = data
                else:
                    self.logger.warning(f"No data returned for FRED indicator {code}")
            except Exception as e:
                self.logger.error(f"Error fetching data for FRED indicator {code}: {str(e)}")

        return result

    def _fetch_alpha_vantage_data(self) -> Dict[str, Any]:
        """
        Fetch economic data from Alpha Vantage.

        Returns:
            Dictionary containing Alpha Vantage economic data
        """
        result = {}

        if not ALPHA_VANTAGE_API_KEY:
            self.logger.warning("Alpha Vantage API key is missing. Skipping Alpha Vantage data.")
            return result

        # Economic indicators to fetch from Alpha Vantage
        indicators = [
            {"function": "REAL_GDP", "interval": "quarterly", "name": "Real GDP"},
            {"function": "CPI", "interval": "monthly", "name": "Consumer Price Index"},
            {"function": "UNEMPLOYMENT", "name": "Unemployment Rate"},
            {"function": "RETAIL_SALES", "name": "Retail Sales"},
            {"function": "NONFARM_PAYROLL", "name": "Nonfarm Payroll"}
        ]

        for indicator in indicators:
            try:
                # Prepare request parameters
                params = {
                    "function": indicator["function"],
                    "apikey": ALPHA_VANTAGE_API_KEY,
                    "datatype": "json"
                }

                if "interval" in indicator:
                    params["interval"] = indicator["interval"]

                # Make API request
                response = requests.get(self.alpha_vantage_url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        result[indicator["function"]] = data
                    else:
                        self.logger.warning(f"No data returned for Alpha Vantage indicator {indicator['function']}")
                else:
                    self.logger.error(f"Error fetching Alpha Vantage data for {indicator['function']}: {response.status_code}")
            except Exception as e:
                self.logger.error(f"Error processing Alpha Vantage data for {indicator['function']}: {str(e)}")

        return result

    def _calculate_economic_summary(self, fred_data: Dict[str, pd.DataFrame], alpha_vantage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate summary statistics for economic indicators.

        Args:
            fred_data: Dictionary of FRED indicator data
            alpha_vantage_data: Dictionary of Alpha Vantage economic data

        Returns:
            Dictionary of economic summary statistics
        """
        summary = {}

        # Process FRED data
        for code, data in fred_data.items():
            if data.empty:
                continue

            # Get the indicator name
            indicator_name = self.default_fred_indicators.get(code, code)

            # Get latest value
            latest_value = data.iloc[-1, 0]

            # Calculate change from previous period
            prev_value = data.iloc[-2, 0] if len(data) > 1 else None
            change = (latest_value - prev_value) if prev_value is not None else None
            change_pct = (change / prev_value * 100) if change is not None and prev_value != 0 else None

            # Get date of latest value
            latest_date = data.index[-1].strftime('%Y-%m-%d')

            summary[indicator_name] = {
                "latest_value": latest_value,
                "latest_date": latest_date,
                "change": change,
                "change_pct": change_pct
            }

        # Process Alpha Vantage data
        for function, data in alpha_vantage_data.items():
            if "data" not in data:
                continue

            # Get the first (most recent) data point
            try:
                latest_data = data["data"][0]
                previous_data = data["data"][1] if len(data["data"]) > 1 else None

                # Extract values
                latest_value = float(latest_data["value"])
                latest_date = latest_data["date"]

                # Calculate change
                change = None
                change_pct = None
                if previous_data:
                    prev_value = float(previous_data["value"])
                    change = latest_value - prev_value
                    change_pct = (change / prev_value * 100) if prev_value != 0 else None

                # Map function to a readable name
                name_mapping = {
                    "REAL_GDP": "Real GDP (Alpha Vantage)",
                    "CPI": "CPI (Alpha Vantage)",
                    "UNEMPLOYMENT": "Unemployment (Alpha Vantage)",
                    "RETAIL_SALES": "Retail Sales (Alpha Vantage)",
                    "NONFARM_PAYROLL": "Nonfarm Payroll (Alpha Vantage)"
                }

                indicator_name = name_mapping.get(function, function)

                summary[indicator_name] = {
                    "latest_value": latest_value,
                    "latest_date": latest_date,
                    "change": change,
                    "change_pct": change_pct
                }
            except (KeyError, IndexError, ValueError) as e:
                self.logger.error(f"Error processing Alpha Vantage data for {function}: {str(e)}")

        return summary

    def format_data_for_report(self, data: Dict[str, Any]) -> str:
        """
        Format economic indicator data for the newsletter.

        Args:
            data: Economic indicator data from fetch_data

        Returns:
            Formatted string for the newsletter
        """
        if "error" in data and data["error"]:
            return f"Error fetching economic indicator data: {data['error']}"

        report = []

        # Format economic summary
        report.append("# Economic Indicators")

        # Group indicators by category
        categories = {
            "Growth": ["GDP", "Real GDP (Alpha Vantage)", "Industrial Production"],
            "Employment": ["Unemployment Rate", "Unemployment (Alpha Vantage)", "Nonfarm Payrolls", "Nonfarm Payroll (Alpha Vantage)"],
            "Inflation": ["CPI", "CPI (Alpha Vantage)"],
            "Interest Rates": ["Fed Funds Rate", "Yield Curve"],
            "Consumer": ["Retail Sales", "Retail Sales (Alpha Vantage)"],
            "Housing": ["Housing Starts"],
            "Money Supply": ["M2 Money Supply"]
        }

        # Add indicators by category
        for category, indicators in categories.items():
            category_indicators = [ind for ind in indicators if ind in data["economic_summary"]]

            if category_indicators:
                report.append(f"## {category}")

                for indicator in category_indicators:
                    metrics = data["economic_summary"][indicator]

                    # Format the value based on the indicator
                    value_str = f"{metrics['latest_value']:.2f}"
                    if "Rate" in indicator or "Unemployment" in indicator:
                        value_str = f"{metrics['latest_value']:.2f}%"

                    # Determine if change is positive or negative
                    change_pct = metrics.get("change_pct")
                    if change_pct is not None:
                        change_symbol = "↑" if change_pct > 0 else "↓"
                        change_str = f"{change_symbol} {abs(change_pct):.2f}%"
                    else:
                        change_str = "N/A"

                    report.append(f"### {indicator}")
                    report.append(f"- Current: {value_str} (as of {metrics['latest_date']})")
                    report.append(f"- Change: {change_str}")
                    report.append("")

        # Add a brief analysis section
        report.append("## Economic Outlook")
        report.append("Based on the latest economic indicators, the overall economic outlook appears to be [analysis will be generated by the language model].")
        report.append("")

        return "\n".join(report)
