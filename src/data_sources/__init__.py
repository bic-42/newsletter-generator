"""
Data sources package for the newsletter generation system.
Contains modules for fetching financial and economic data from various sources.
"""

from .base import DataSource
from .stock_market import StockMarketData
from .economic_indicators import EconomicIndicators
from .news_headlines import NewsHeadlines
from .crypto_data import CryptoDataSource

__all__ = ['DataSource', 'StockMarketData', 'EconomicIndicators', 'NewsHeadlines']