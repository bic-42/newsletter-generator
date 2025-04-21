"""
Module for fetching stock market data using yfinance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import numpy as np

from .base import DataSource

class StockMarketData(DataSource):
    """
    Data source for stock market information.
    
    Fetches data about major indices, top gainers/losers, and market trends.
    """
    
    def __init__(self):
        """Initialize the stock market data source."""
        super().__init__(name="Stock Market Data")
        
        # Default indices to track
        self.default_indices = [
            "^GSPC",    # S&P 500
            "^DJI",     # Dow Jones Industrial Average
            "^IXIC",    # NASDAQ Composite
            "^RUT",     # Russell 2000
            "^VIX",     # CBOE Volatility Index
            "^FTSE",    # FTSE 100
            "^N225"     # Nikkei 225
        ]
        
        # Default stocks to track (top tech companies)
        self.default_stocks = [
            "AAPL",     # Apple
            "MSFT",     # Microsoft
            "GOOGL",    # Alphabet (Google)
            "AMZN",     # Amazon
            "META",     # Meta (Facebook)
            "TSLA",     # Tesla
            "NVDA",     # NVIDIA
            "JPM",      # JPMorgan Chase
            "V",        # Visa
            "WMT"       # Walmart
        ]
    
    def fetch_data(self, 
                  indices: Optional[List[str]] = None, 
                  stocks: Optional[List[str]] = None, 
                  days: int = 7) -> Dict[str, Any]:
        """
        Fetch stock market data.
        
        Args:
            indices: List of index symbols to fetch (defaults to self.default_indices)
            stocks: List of stock symbols to fetch (defaults to self.default_stocks)
            days: Number of days of historical data to fetch
            
        Returns:
            Dictionary containing market data
        """
        self.log_fetch_attempt(indices=indices, stocks=stocks, days=days)
        
        try:
            # Use default lists if none provided
            indices = indices or self.default_indices
            stocks = stocks or self.default_stocks
            
            # Get date range
            start_date, end_date = self.get_date_range(days)
            
            # Fetch index data
            index_data = self._fetch_ticker_data(indices, start_date, end_date)
            
            # Fetch stock data
            stock_data = self._fetch_ticker_data(stocks, start_date, end_date)
            
            # Calculate market summary
            market_summary = self._calculate_market_summary(index_data)
            
            # Calculate stock performance
            stock_performance = self._calculate_stock_performance(stock_data)
            
            # Prepare result
            result = {
                "market_summary": market_summary,
                "stock_performance": stock_performance,
                "raw_data": {
                    "indices": index_data,
                    "stocks": stock_data
                }
            }
            
            self.log_fetch_success(len(index_data) + len(stock_data))
            return result
            
        except Exception as e:
            self.log_fetch_error(e)
            # Return empty data with error information
            return {
                "error": str(e),
                "market_summary": {},
                "stock_performance": {},
                "raw_data": {"indices": {}, "stocks": {}}
            }
    
    def _fetch_ticker_data(self, tickers: List[str], start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for a list of ticker symbols.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Dictionary mapping ticker symbols to their data
        """
        result = {}
        
        for ticker in tickers:
            try:
                # Fetch data from yfinance
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                
                if not data.empty:
                    result[ticker] = data
                else:
                    self.logger.warning(f"No data returned for ticker {ticker}")
            except Exception as e:
                self.logger.error(f"Error fetching data for ticker {ticker}: {str(e)}")
        
        return result
    
    def _calculate_market_summary(self, index_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Calculate summary statistics for market indices.
        
        Args:
            index_data: Dictionary of index data
            
        Returns:
            Dictionary of market summary statistics
        """
        summary = {}
        
        for index, data in index_data.items():
            if data.empty:
                continue
                
            # Calculate daily returns
            data['Daily Return'] = data['Close'].pct_change()
            
            # Get latest close price
            latest_close = data['Close'].iloc[-1]
            
            # Calculate change from previous day
            prev_close = data['Close'].iloc[-2] if len(data) > 1 else None
            daily_change = (latest_close - prev_close) / prev_close * 100 if prev_close else None
            
            # Calculate weekly change
            week_ago_close = data['Close'].iloc[0] if len(data) > 5 else None
            weekly_change = (latest_close - week_ago_close) / week_ago_close * 100 if week_ago_close else None
            
            # Calculate volatility (standard deviation of returns)
            volatility = data['Daily Return'].std() * 100
            
            summary[index] = {
                "latest_close": latest_close,
                "daily_change_pct": daily_change,
                "weekly_change_pct": weekly_change,
                "volatility": volatility
            }
        
        return summary
    
    def _calculate_stock_performance(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Calculate performance metrics for stocks.
        
        Args:
            stock_data: Dictionary of stock data
            
        Returns:
            Dictionary of stock performance metrics
        """
        performance = {}
        
        # Calculate performance for each stock
        for ticker, data in stock_data.items():
            if data.empty:
                continue
                
            # Calculate daily returns
            data['Daily Return'] = data['Close'].pct_change()
            
            # Get latest close price
            latest_close = data['Close'].iloc[-1]
            
            # Calculate change from previous day
            prev_close = data['Close'].iloc[-2] if len(data) > 1 else None
            daily_change = (latest_close - prev_close) / prev_close * 100 if prev_close else None
            
            # Calculate weekly change
            week_ago_close = data['Close'].iloc[0] if len(data) > 5 else None
            weekly_change = (latest_close - week_ago_close) / week_ago_close * 100 if week_ago_close else None
            
            # Calculate volume change
            latest_volume = data['Volume'].iloc[-1]
            prev_volume = data['Volume'].iloc[-2] if len(data) > 1 else None
            volume_change = (latest_volume - prev_volume) / prev_volume * 100 if prev_volume else None
            
            performance[ticker] = {
                "latest_close": latest_close,
                "daily_change_pct": daily_change,
                "weekly_change_pct": weekly_change,
                "latest_volume": latest_volume,
                "volume_change_pct": volume_change
            }
        
        # Sort stocks by performance
        if performance:
            # Find top gainers and losers
            sorted_by_daily = sorted(performance.items(), key=lambda x: x[1]["daily_change_pct"] if x[1]["daily_change_pct"] is not None else -float('inf'), reverse=True)
            top_gainers = dict(sorted_by_daily[:3])
            top_losers = dict(sorted_by_daily[-3:])
            
            performance = {
                "all_stocks": performance,
                "top_gainers": top_gainers,
                "top_losers": top_losers
            }
        
        return performance
    
    def format_data_for_report(self, data: Dict[str, Any]) -> str:
        """
        Format stock market data for the newsletter.
        
        Args:
            data: Stock market data from fetch_data
            
        Returns:
            Formatted string for the newsletter
        """
        if "error" in data and data["error"]:
            return f"Error fetching stock market data: {data['error']}"
        
        report = []
        
        # Format market summary
        report.append("# Market Summary")
        
        for index, metrics in data["market_summary"].items():
            index_name = self._get_index_name(index)
            daily_change = metrics["daily_change_pct"]
            change_symbol = "↑" if daily_change and daily_change > 0 else "↓"
            
            report.append(f"## {index_name}")
            report.append(f"- Current: {metrics['latest_close']:.2f}")
            report.append(f"- Daily Change: {change_symbol} {abs(daily_change):.2f}%" if daily_change is not None else "- Daily Change: N/A")
            report.append(f"- Weekly Change: {metrics['weekly_change_pct']:.2f}%" if metrics['weekly_change_pct'] is not None else "- Weekly Change: N/A")
            report.append("")
        
        # Format top gainers
        report.append("# Top Performing Stocks")
        for ticker, metrics in data["stock_performance"].get("top_gainers", {}).items():
            report.append(f"## {ticker}")
            report.append(f"- Current: ${metrics['latest_close']:.2f}")
            report.append(f"- Daily Change: ↑ {metrics['daily_change_pct']:.2f}%" if metrics['daily_change_pct'] is not None else "- Daily Change: N/A")
            report.append("")
        
        # Format top losers
        report.append("# Underperforming Stocks")
        for ticker, metrics in data["stock_performance"].get("top_losers", {}).items():
            report.append(f"## {ticker}")
            report.append(f"- Current: ${metrics['latest_close']:.2f}")
            report.append(f"- Daily Change: ↓ {abs(metrics['daily_change_pct']):.2f}%" if metrics['daily_change_pct'] is not None else "- Daily Change: N/A")
            report.append("")
        
        return "\n".join(report)
    
    def _get_index_name(self, symbol: str) -> str:
        """
        Get the full name of an index from its symbol.
        
        Args:
            symbol: The index symbol
            
        Returns:
            The full name of the index
        """
        index_names = {
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones Industrial Average",
            "^IXIC": "NASDAQ Composite",
            "^RUT": "Russell 2000",
            "^VIX": "CBOE Volatility Index",
            "^FTSE": "FTSE 100",
            "^N225": "Nikkei 225"
        }
        
        return index_names.get(symbol, symbol)