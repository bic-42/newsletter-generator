"""
Module for fetching stock market data using yfinance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import numpy as np

# Assuming your base class and logger setup are correct
from .base import DataSource
# Import the logger from config or base (ensure self.logger is initialized correctly)
import logging

class StockMarketData(DataSource):
    """
    Data source for stock market information.

    Fetches data about major indices, top gainers/losers, and market trends.
    """

    def __init__(self):
        """Initialize the stock market data source."""
        # Ensure the base class initializes self.logger
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
            "AAPL", "MSFT", "GOOGL", "AMZN", "META",
            "TSLA", "NVDA", "JPM", "V", "WMT"
        ]


    def fetch_data(self,
                   indices: Optional[List[str]] = None,
                   stocks: Optional[List[str]] = None,
                   days: int = 30) -> Dict[str, Any]:
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
            if indices is None:
                indices = self.default_indices
            if stocks is None:
                stocks = self.default_stocks

            # Get date range
            start_date, end_date = self.get_date_range(days)

            # Fetch index data
            self.logger.info("Fetching index data...")
            index_data = self._fetch_ticker_data(indices, start_date, end_date)

            # Fetch stock data
            self.logger.info("Fetching stock data...")
            stock_data = self._fetch_ticker_data(stocks, start_date, end_date)

            # Calculate market summary
            self.logger.info("Calculating market summary...")
            market_summary = self._calculate_market_summary(index_data)

            # Calculate stock performance
            self.logger.info("Calculating stock performance...")
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
            self.log_fetch_error(e) # Log the error using the base class method
            # Return empty data with error information - original behavior restored
            return {
                "error": str(e),
                "market_summary": {},
                "stock_performance": {},
                "raw_data": {"indices": {}, "stocks": {},}
            }

    def _fetch_ticker_data(self, tickers: List[str], start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """ Fetches data and corrects potential column MultiIndex issue from yfinance """
        result = {}
        for ticker in tickers:
            self.logger.info(f"Attempting to fetch data for ticker: {ticker}")
            try:
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)

                # --- FIX: Check for and simplify COLUMN MultiIndex ---
                if not data.empty and isinstance(data.columns, pd.MultiIndex):
                    self.logger.warning(f"Detected COLUMN MultiIndex for single ticker {ticker}. Adjusting structure.")
                    original_columns = data.columns
                    try:
                        # Get the values from the FIRST level (index 0, e.g., 'Price')
                        data.columns = data.columns.get_level_values(0)
                        self.logger.info(f"Adjusted columns for {ticker}: {data.columns}")
                    except Exception as col_fix_e:
                        # Log error if fix fails, but try to continue
                        self.logger.error(f"Failed to get_level_values(0) on columns for {ticker}. Original cols: {original_columns}. Error: {col_fix_e}", exc_info=True)

                # (Fallback check for INDEX MultiIndex, though less likely cause)
                elif not data.empty and isinstance(data.index, pd.MultiIndex):
                    self.logger.warning(f"Detected INDEX MultiIndex for single ticker {ticker}. Resetting index.")
                    try:
                        data.index = data.index.get_level_values('Date')
                    except KeyError:
                        self.logger.warning(f"'Date' level not found in index MultiIndex for {ticker}, using level 0.")
                        data.index = data.index.get_level_values(0)
                    self.logger.debug(f"Corrected data index for {ticker}: {data.index}")
                # --- End FIX ---


                if not data.empty:
                    result[ticker] = data
                    # Optionally log success here if desired
                else:
                    self.logger.warning(f"No data returned for ticker {ticker}")

            except Exception as e:
                # Log error specific to this ticker fetch
                self.logger.error(f"Error fetching or processing data for ticker {ticker}: {str(e)}", exc_info=True)
                # Continue to next ticker instead of failing the whole fetch
                continue
        return result


    def _calculate_market_summary(self, index_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """ Calculate summary statistics for market indices with robust checks """
        summary = {}

        for index, data in index_data.items():
            # Ensure data is not empty and has the required columns
            if data.empty or 'Close' not in data.columns or 'Volume' not in data.columns:
                self.logger.warning(f"Data for index {index} is empty or missing required columns. Skipping summary.")
                continue

            try:
                # Calculate daily returns - requires 'Close' column
                data['Daily Return'] = data['Close'].pct_change()

                # Get latest close price
                latest_close = data['Close'].iloc[-1]
                # Basic check if it's somehow still not a scalar (unlikely now)
                if isinstance(latest_close, (pd.Series, pd.DataFrame)):
                    self.logger.error(f"latest_close is unexpected type for {index}: {type(latest_close)}. Skipping summary.")
                    continue

                # --- Robust Calculation for Daily Change ---
                daily_change = None
                if len(data) > 1:
                    prev_close = data['Close'].iloc[-2]
                    # Check type and value before calculation
                    if not isinstance(prev_close, (pd.Series, pd.DataFrame)):
                        if pd.notna(prev_close) and prev_close != 0:
                            daily_change = (latest_close - prev_close) / prev_close * 100
                        elif prev_close == 0:
                            self.logger.warning(f"Previous close was zero for index {index}. Cannot calculate daily change.")
                    else:
                         self.logger.error(f"prev_close is unexpected type for {index}: {type(prev_close)}")
                else:
                    self.logger.warning(f"Not enough data points for index {index} to calculate daily change.")
                # --- End Robust Calculation ---

                # --- Robust Calculation for Weekly Change ---
                weekly_change = None
                if len(data) > 5: # Need at least 6 rows for 5 trading days prior
                    week_ago_close = data['Close'].iloc[0]
                    # Check type and value before calculation
                    if not isinstance(week_ago_close, (pd.Series, pd.DataFrame)):
                        if pd.notna(week_ago_close) and week_ago_close != 0:
                             weekly_change = (latest_close - week_ago_close) / week_ago_close * 100
                        elif week_ago_close == 0:
                             self.logger.warning(f"Week ago close was zero for index {index}. Cannot calculate weekly change.")
                    else:
                        self.logger.error(f"week_ago_close is unexpected type for {index}: {type(week_ago_close)}")
                else:
                    self.logger.warning(f"Not enough data points for index {index} to calculate weekly change.")

                # Calculate volatility - check if 'Daily Return' column exists and has values
                volatility = None
                if 'Daily Return' in data.columns and data['Daily Return'].notna().any():
                     volatility = data['Daily Return'].std() * 100
                     if isinstance(volatility, (pd.Series, pd.DataFrame)): # Should be scalar
                          self.logger.error(f"volatility is unexpected type for {index}: {type(volatility)}")
                          volatility = None # Reset if calculation failed
                else:
                     self.logger.warning(f"Cannot calculate volatility for index {index} due to missing/NaN returns.")


                summary[index] = {
                    "latest_close": latest_close,
                    "daily_change_pct": daily_change,
                    "weekly_change_pct": weekly_change,
                    "volatility": volatility
                }

            except Exception as calc_e:
                 # Log error specific to calculation for this index
                 self.logger.error(f"Exception during summary calculation for index {index}: {calc_e}", exc_info=True)
                 # Continue to next index
                 continue

        return summary

    def _calculate_stock_performance(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Calculate performance metrics for stocks.
        Assumes stock_data contains DataFrames corrected by _fetch_ticker_data.
        """
        performance = {}
        all_stocks_perf = {} # Store individual performance before sorting

        for ticker, data in stock_data.items():
             # Ensure data is not empty and has the required columns
            if data.empty or 'Close' not in data.columns or 'Volume' not in data.columns:
                self.logger.warning(f"Data for stock {ticker} is empty or missing required columns. Skipping performance calculation.")
                continue

            try:
                # Calculate daily returns
                data['Daily Return'] = data['Close'].pct_change()

                # Get latest close price
                latest_close = data['Close'].iloc[-1]
                if isinstance(latest_close, (pd.Series, pd.DataFrame)): # Robustness check
                    self.logger.error(f"latest_close is unexpected type for {ticker}. Skipping performance.")
                    continue

                # Calculate daily change
                daily_change = None
                if len(data) > 1:
                    prev_close = data['Close'].iloc[-2]
                    if not isinstance(prev_close, (pd.Series, pd.DataFrame)):
                        if pd.notna(prev_close) and prev_close != 0:
                            daily_change = (latest_close - prev_close) / prev_close * 100
                        elif prev_close == 0:
                             self.logger.warning(f"Previous close was zero for stock {ticker}.")
                    else:
                         self.logger.error(f"prev_close is unexpected type for {ticker}: {type(prev_close)}")

                # Calculate weekly change
                weekly_change = None
                if len(data) > 5:
                    week_ago_close = data['Close'].iloc[0]
                    if not isinstance(week_ago_close, (pd.Series, pd.DataFrame)):
                        if pd.notna(week_ago_close) and week_ago_close != 0:
                             weekly_change = (latest_close - week_ago_close) / week_ago_close * 100
                        elif week_ago_close == 0:
                            self.logger.warning(f"Week ago close was zero for stock {ticker}.")
                    else:
                        self.logger.error(f"week_ago_close is unexpected type for {ticker}: {type(week_ago_close)}")


                # Calculate volume change
                latest_volume = data['Volume'].iloc[-1]
                volume_change = None
                if len(data) > 1:
                    prev_volume = data['Volume'].iloc[-2]
                    if not isinstance(prev_volume, (pd.Series, pd.DataFrame)):
                        if pd.notna(prev_volume) and prev_volume != 0:
                             volume_change = (latest_volume - prev_volume) / prev_volume * 100
                        elif prev_volume == 0:
                            self.logger.warning(f"Previous volume was zero for stock {ticker}.")
                    else:
                        self.logger.error(f"prev_volume is unexpected type for {ticker}: {type(prev_volume)}")


                all_stocks_perf[ticker] = {
                    "latest_close": latest_close,
                    "daily_change_pct": daily_change,
                    "weekly_change_pct": weekly_change,
                    "latest_volume": latest_volume if not isinstance(latest_volume, (pd.Series, pd.DataFrame)) else None,
                    "volume_change_pct": volume_change
                }

            except Exception as calc_e:
                 self.logger.error(f"Exception during performance calculation for stock {ticker}: {calc_e}", exc_info=True)
                 continue # Continue to next stock


        # Sort stocks by performance *after* calculating all
        if all_stocks_perf:
            # Handle potential None values in daily_change_pct during sorting
            sorted_by_daily = sorted(
                all_stocks_perf.items(),
                key=lambda item: item[1].get("daily_change_pct", -float('inf')) if item[1].get("daily_change_pct") is not None else -float('inf'),
                reverse=True
            )
            # Ensure we take max 3, even if fewer stocks were processed
            top_gainers = dict(sorted_by_daily[:min(3, len(sorted_by_daily))])
            # Ensure we take max 3 from the end
            top_losers = dict(sorted_by_daily[max(0, len(sorted_by_daily)-3):])

            performance = {
                "all_stocks": all_stocks_perf,
                "top_gainers": top_gainers,
                "top_losers": top_losers
            }

        return performance

    def format_data_for_report(self, data: Dict[str, Any]) -> str:
        """
        Format stock market data for the newsletter.
        """
        # Check for error at the beginning
        if data.get("error"):
            return f"Error fetching stock market data: {data['error']}"

        # Check if essential data keys are missing or empty
        market_summary = data.get("market_summary")
        stock_performance = data.get("stock_performance")

        if not market_summary and not stock_performance:
             return "No stock market data available to report."

        report = []

        # Format market summary
        report.append("# Market Summary")
        if market_summary:
             for index, metrics in market_summary.items():
                index_name = self._get_index_name(index)
                report.append(f"## {index_name}")

                latest_close = metrics.get("latest_close", "N/A")
                if isinstance(latest_close, (float, int)):
                     report.append(f"- Current: {latest_close:.2f}")
                else:
                     report.append(f"- Current: {latest_close}") # Handles "Error: Series" or None

                daily_change = metrics.get("daily_change_pct")
                if daily_change is not None and isinstance(daily_change, (float, int)):
                     change_symbol = "↑" if daily_change > 0 else "↓" if daily_change < 0 else "→"
                     report.append(f"- Daily Change: {change_symbol} {abs(daily_change):.2f}%")
                else:
                     report.append("- Daily Change: N/A")

                weekly_change = metrics.get("weekly_change_pct")
                if weekly_change is not None and isinstance(weekly_change, (float, int)):
                     report.append(f"- Weekly Change: {weekly_change:.2f}%")
                else:
                     report.append("- Weekly Change: N/A")
                report.append("")
        else:
             report.append("No market summary data available.")
             report.append("")

        # Format stock performance if available
        if stock_performance and stock_performance.get("all_stocks"):
             top_gainers = stock_performance.get("top_gainers", {})
             top_losers = stock_performance.get("top_losers", {})

             if top_gainers:
                report.append("# Top Performing Stocks")
                for ticker, metrics in top_gainers.items():
                     report.append(f"## {ticker}")
                     latest_close = metrics.get("latest_close", "N/A")
                     if isinstance(latest_close, (float, int)):
                         report.append(f"- Current: ${latest_close:.2f}")
                     else:
                         report.append(f"- Current: ${latest_close}")

                     daily_change = metrics.get("daily_change_pct")
                     if daily_change is not None and isinstance(daily_change, (float, int)):
                         report.append(f"- Daily Change: ↑ {daily_change:.2f}%")
                     else:
                         report.append("- Daily Change: N/A")
                     report.append("")
             else:
                report.append("# Top Performing Stocks")
                report.append("No top gainers data available.")
                report.append("")


             if top_losers:
                 report.append("# Underperforming Stocks")
                 # Sort losers by change ASCENDING to show most negative first
                 sorted_losers = sorted(top_losers.items(), key=lambda item: item[1].get("daily_change_pct", float('inf')) if item[1].get("daily_change_pct") is not None else float('inf'))
                 for ticker, metrics in sorted_losers:
                     report.append(f"## {ticker}")
                     latest_close = metrics.get("latest_close", "N/A")
                     if isinstance(latest_close, (float, int)):
                         report.append(f"- Current: ${latest_close:.2f}")
                     else:
                         report.append(f"- Current: ${latest_close}")

                     daily_change = metrics.get("daily_change_pct")
                     if daily_change is not None and isinstance(daily_change, (float, int)):
                         # Use abs() since we know these are losers (or zero)
                         report.append(f"- Daily Change: ↓ {abs(daily_change):.2f}%")
                     else:
                         report.append("- Daily Change: N/A")
                     report.append("")
             else:
                report.append("# Underperforming Stocks")
                report.append("No underperforming stocks data available.")
                report.append("")

        else:
             report.append("# Stock Performance")
             report.append("No stock performance data available.")
             report.append("")


        return "\n".join(report)

    def _get_index_name(self, symbol: str) -> str:
        """ Get the full name of an index from its symbol. """
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