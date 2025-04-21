"""
Module for fetching financial news headlines from various sources.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import json
import re

from .base import DataSource
from config.logger import logger

class NewsHeadlines(DataSource):
    """
    Data source for financial news headlines.

    Fetches recent financial news from various sources.
    """

    def __init__(self):
        """Initialize the news headlines data source."""
        super().__init__(name="Financial News Headlines")

        # Default news sources
        self.default_sources = [
            {
                "name": "Yahoo Finance",
                "url": "https://finance.yahoo.com/news/",
                "parser": self._parse_yahoo_finance
            },
            {
                "name": "CNBC",
                "url": "https://www.cnbc.com/finance/",
                "parser": self._parse_cnbc
            },
            {
                "name": "Bloomberg",
                "url": "https://www.bloomberg.com/markets",
                "parser": self._parse_bloomberg
            }
        ]

    def fetch_data(self, 
                  sources: Optional[List[Dict[str, Any]]] = None,
                  max_headlines: int = 10) -> Dict[str, Any]:
        """
        Fetch financial news headlines.

        Args:
            sources: List of news sources to fetch from (defaults to self.default_sources)
            max_headlines: Maximum number of headlines to fetch per source

        Returns:
            Dictionary containing news headlines
        """
        self.log_fetch_attempt(sources=[s.get("name") for s in (sources or self.default_sources)], 
                              max_headlines=max_headlines)

        try:
            # Use default sources if none provided
            sources = sources or self.default_sources

            # Fetch headlines from each source
            all_headlines = []
            source_headlines = {}

            for source in sources:
                try:
                    headlines = self._fetch_from_source(source, max_headlines)
                    source_headlines[source["name"]] = headlines
                    all_headlines.extend(headlines)
                except Exception as e:
                    self.logger.error(f"Error fetching headlines from {source['name']}: {str(e)}")

            # Sort all headlines by date (most recent first)
            all_headlines.sort(key=lambda x: x.get("date", datetime.min), reverse=True)

            # Prepare result
            result = {
                "all_headlines": all_headlines[:max_headlines],
                "source_headlines": source_headlines
            }

            self.log_fetch_success(len(all_headlines))
            return result

        except Exception as e:
            self.log_fetch_error(e)
            # Return empty data with error information
            return {
                "error": str(e),
                "all_headlines": [],
                "source_headlines": {}
            }

    def _fetch_from_source(self, source: Dict[str, Any], max_headlines: int) -> List[Dict[str, Any]]:
        """
        Fetch headlines from a specific source.

        Args:
            source: Source configuration
            max_headlines: Maximum number of headlines to fetch

        Returns:
            List of headline dictionaries
        """
        try:
            # Make HTTP request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(source["url"], headers=headers, timeout=10)

            if response.status_code == 200:
                # Parse the response using the source-specific parser
                headlines = source["parser"](response.text, max_headlines)

                # Add source name to each headline
                for headline in headlines:
                    headline["source"] = source["name"]

                return headlines
            else:
                self.logger.error(f"Error fetching from {source['name']}: HTTP {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error in _fetch_from_source for {source['name']}: {str(e)}")
            return []

    def _parse_yahoo_finance(self, html_content: str, max_headlines: int) -> List[Dict[str, Any]]:
        """
        Parse Yahoo Finance news page.

        Args:
            html_content: HTML content of the page
            max_headlines: Maximum number of headlines to extract

        Returns:
            List of headline dictionaries
        """
        headlines = []
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find news articles
        articles = soup.find_all('div', {'class': 'Ov(h)'})

        for article in articles[:max_headlines]:
            try:
                # Extract headline
                headline_elem = article.find('h3')
                if not headline_elem:
                    continue

                headline = headline_elem.text.strip()

                # Extract URL
                link_elem = headline_elem.find('a')
                url = f"https://finance.yahoo.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else None

                # Extract summary
                summary_elem = article.find('p')
                summary = summary_elem.text.strip() if summary_elem else None

                # Extract date (Yahoo Finance usually has relative dates like "1h ago")
                date_elem = article.find('span', {'class': 'C($tertiaryColor)'})
                date_text = date_elem.text.strip() if date_elem else None
                date = self._parse_relative_date(date_text) if date_text else datetime.now()

                headlines.append({
                    "headline": headline,
                    "url": url,
                    "summary": summary,
                    "date": date,
                    "date_str": date.strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                self.logger.error(f"Error parsing Yahoo Finance article: {str(e)}")

        return headlines

    def _parse_cnbc(self, html_content: str, max_headlines: int) -> List[Dict[str, Any]]:
        """
        Parse CNBC news page.

        Args:
            html_content: HTML content of the page
            max_headlines: Maximum number of headlines to extract

        Returns:
            List of headline dictionaries
        """
        headlines = []
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find news articles
        articles = soup.find_all('div', {'class': 'Card-titleContainer'})

        for article in articles[:max_headlines]:
            try:
                # Extract headline
                headline_elem = article.find('a', {'class': 'Card-title'})
                if not headline_elem:
                    continue

                headline = headline_elem.text.strip()

                # Extract URL
                url = headline_elem['href'] if 'href' in headline_elem.attrs else None

                # CNBC doesn't always have summaries in the card view
                summary = None

                # Extract date
                date_elem = article.find('span', {'class': 'Card-time'})
                date_text = date_elem.text.strip() if date_elem else None
                date = self._parse_relative_date(date_text) if date_text else datetime.now()

                headlines.append({
                    "headline": headline,
                    "url": url,
                    "summary": summary,
                    "date": date,
                    "date_str": date.strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                self.logger.error(f"Error parsing CNBC article: {str(e)}")

        return headlines

    def _parse_bloomberg(self, html_content: str, max_headlines: int) -> List[Dict[str, Any]]:
        """
        Parse Bloomberg news page.

        Args:
            html_content: HTML content of the page
            max_headlines: Maximum number of headlines to extract

        Returns:
            List of headline dictionaries
        """
        headlines = []
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find news articles
        articles = soup.find_all('article', {'class': 'story-package-module__story'})

        for article in articles[:max_headlines]:
            try:
                # Extract headline
                headline_elem = article.find('h3', {'class': 'story-package-module__headline'})
                if not headline_elem:
                    continue

                headline = headline_elem.text.strip()

                # Extract URL
                link_elem = article.find('a')
                url = f"https://www.bloomberg.com{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else None

                # Extract summary
                summary_elem = article.find('p', {'class': 'story-package-module__summary'})
                summary = summary_elem.text.strip() if summary_elem else None

                # Bloomberg doesn't always show dates on the main page
                # Use current date as fallback
                date = datetime.now()

                headlines.append({
                    "headline": headline,
                    "url": url,
                    "summary": summary,
                    "date": date,
                    "date_str": date.strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                self.logger.error(f"Error parsing Bloomberg article: {str(e)}")

        return headlines

    def _parse_relative_date(self, date_text: str) -> datetime:
        """
        Parse relative date strings like "1h ago", "2d ago", etc.

        Args:
            date_text: Relative date text

        Returns:
            datetime object
        """
        now = datetime.now()

        if not date_text:
            return now

        # Convert to lowercase for easier matching
        date_text = date_text.lower()

        # Match patterns like "1h ago", "2d ago", etc.
        match = re.search(r'(\d+)\s*([hdwmy])', date_text)
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if unit == 'h':  # hours
                return now - timedelta(hours=value)
            elif unit == 'd':  # days
                return now - timedelta(days=value)
            elif unit == 'w':  # weeks
                return now - timedelta(weeks=value)
            elif unit == 'm':  # months (approximate)
                return now - timedelta(days=value * 30)
            elif unit == 'y':  # years (approximate)
                return now - timedelta(days=value * 365)

        # If we can't parse it, return current time
        return now

    def format_data_for_report(self, data: Dict[str, Any]) -> str:
        """
        Format news headlines for the newsletter.

        Args:
            data: News headline data from fetch_data

        Returns:
            Formatted string for the newsletter
        """
        if "error" in data and data["error"]:
            return f"Error fetching news headlines: {data['error']}"

        report = []

        # Format headlines
        report.append("# Financial News Headlines")

        if data["all_headlines"]:
            for headline in data["all_headlines"]:
                report.append(f"## {headline['headline']}")

                if headline.get("summary"):
                    report.append(f"{headline['summary']}")

                source_date = f"{headline['source']} - {headline['date_str']}"
                report.append(f"*Source: {source_date}*")

                if headline.get("url"):
                    report.append(f"[Read more]({headline['url']})")

                report.append("")
        else:
            report.append("No recent headlines available.")

        return "\n".join(report)
