# src/data_sources/crypto_data.py

import requests
import pandas as pd
import json
from pycoingecko import CoinGeckoAPI
from ..config import COINGECKO_API_KEY
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .base import DataSource
# from pycoingecko import CoinGeckoAPI # Example library, install if using
import logging
import time # For potential rate limiting delays

logger = logging.getLogger(__name__)

# Define known stablecoin symbols (lowercase for case-insensitive matching)
# Expand this list as needed based on API results
STABLECOIN_SYMBOLS = {'usdt', 'usdc', 'busd', 'dai', 'tusd', 'usdp', 'ust', 'frax', 'lusd', 'fei', 'gusd', 'usdd'}

class CryptoDataSource(DataSource):
    """
    Data source for top cryptocurrencies by market cap.
    Uses CoinGecko API (example).
    """
    def __init__(self):
        super().__init__(name="Cryptocurrency Data")
        # --- Option 1: Using pycoingecko library ---
        try:
            self.coingecko_api_url = "https://api.coingecko.com"
            self.cg = CoinGeckoAPI(demo_api_key=COINGECKO_API_KEY)
            # Test connection
            self.cg.ping()
            logger.info("CoinGeckoAPI client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize CoinGeckoAPI: {e}")
            self.cg = None

        # --- Option 2: Using direct requests ---
        # self.coingecko_api_url = "https://api.coingecko.com/api/v3"
        # logger.info("CryptoDataSource initialized for direct CoinGecko requests.")
        # # No API key needed for public endpoints used here, but rate limits apply


    def _get_top_crypto_data(self, top_n: int = 10, exclude_stablecoins: bool = True) -> List[Dict[str, Any]]:
        """
        Fetches top N cryptocurrencies by market cap from CoinGecko, excluding stablecoins.
        """
        logger.info(f"Fetching top {top_n} crypto data from CoinGecko...")
        coins_to_fetch = top_n + 10 # Fetch slightly more to account for filtering stablecoins
        endpoint = f"{self.coingecko_api_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': coins_to_fetch,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '24h,7d' # Request % changes
        }
        headers = {'accept': 'application/json'}
        filtered_coins_data = []

        try:
            # --- Make the API Call ---
            response = requests.get(endpoint, params=params, headers=headers, timeout=15)
            response.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)
            raw_data = response.json()
            # --- API Call Success ---

            count = 0
            for coin in raw_data:
                if count >= top_n:
                    break # Stop once we have enough non-stablecoins

                symbol = coin.get('symbol', '').lower()
                # Filter stablecoins
                if exclude_stablecoins and symbol in STABLECOIN_SYMBOLS:
                    logger.debug(f"Skipping stablecoin: {coin.get('name')} ({symbol})")
                    continue

                # Extract relevant info (adjust keys based on actual API response if needed)
                coin_info = {
                    "id": coin.get('id'),
                    "symbol": symbol.upper(), # Store uppercase symbol
                    "name": coin.get('name'),
                    "latest_price": coin.get('current_price'),
                    "market_cap": coin.get('market_cap'),
                    "daily_change_pct": coin.get('price_change_percentage_24h'),
                    # Note: CoinGecko API might return 7d change under a different key, adjust if needed
                    "weekly_change_pct": coin.get('price_change_percentage_7d_in_currency'),
                    "rank": coin.get('market_cap_rank')
                }
                # Basic validation that we have key data
                if coin_info['symbol'] and coin_info['name'] and coin_info['latest_price'] is not None:
                     filtered_coins_data.append(coin_info)
                     count += 1
                else:
                     logger.warning(f"Incomplete data for coin: {coin.get('id')}, skipping.")


            if count < top_n:
                 logger.warning(f"Could only fetch {count} non-stablecoin cryptos (requested {top_n}).")


        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Error fetching CoinGecko data: {e}", exc_info=True)
        except json.JSONDecodeError as e:
             logger.error(f"Error decoding CoinGecko JSON response: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch or parse top crypto data: {e}", exc_info=True)

        return filtered_coins_data


    def fetch_data(self, top_n: int = 10, exclude_stablecoins: bool = True) -> Dict[str, Any]:
        """ Fetches and processes top cryptocurrency data """
        self.log_fetch_attempt(top_n=top_n, exclude_stablecoins=exclude_stablecoins)
        try:
            # Potentially add a small delay to respect rate limits if needed
            # time.sleep(1) # Add delay if hitting rate limits frequently
            top_crypto_data = self._get_top_crypto_data(top_n=top_n, exclude_stablecoins=exclude_stablecoins)

            if not top_crypto_data:
                 # Raise specific error or return empty with warning
                 logger.warning("No crypto data could be fetched.")
                 # Optionally return an error structure:
                 # return {"error": "Failed to fetch crypto data", "top_cryptos": []}

            result = {
                "top_cryptos": top_crypto_data
            }
            self.log_fetch_success(len(top_crypto_data))
            return result

        except Exception as e:
            self.log_fetch_error(e)
            return {"error": str(e), "top_cryptos": []}


    def format_data_for_report(self, data: Dict[str, Any]) -> str:
        """ Formats the top crypto data into a Markdown table """
        if data.get("error"):
            return f"# Cryptocurrency Update\n\n_Error fetching crypto data: {data['error']}_"

        top_cryptos = data.get("top_cryptos", [])

        if not top_cryptos:
            return "# Cryptocurrency Update\n\n_No cryptocurrency data available._"

        report = ["# Cryptocurrency Market Highlights"] # Changed title slightly
        # Create a markdown table
        report.append("| Rank | Name (Symbol) | Price (USD) | 24h Change | 7d Change | Market Cap |")
        report.append("|---|---|---|---|---|---|") # Markdown table separator

        # No need to sort again if API returns sorted by market cap rank
        for crypto in top_cryptos:
            rank = crypto.get('rank', 'N/A')
            name = crypto.get('name', 'N/A')
            symbol = crypto.get('symbol', 'N/A')
            price = crypto.get('latest_price', None)
            change_24h = crypto.get('daily_change_pct', None)
            change_7d = crypto.get('weekly_change_pct', None) # Use the correct key
            market_cap = crypto.get('market_cap', None)

            # Format values nicely
            price_str = f"${price:,.2f}" if isinstance(price, (int, float)) else "N/A"

            change_24h_str = "N/A"
            if isinstance(change_24h, (int, float)):
                # Using simpler up/down arrows for text
                change_24h_symbol = "↑" if change_24h > 0 else "↓" if change_24h < 0 else ""
                change_24h_str = f"{change_24h_symbol}{abs(change_24h):.2f}%"

            change_7d_str = "N/A"
            if isinstance(change_7d, (int, float)):
                change_7d_symbol = "↑" if change_7d > 0 else "↓" if change_7d < 0 else ""
                change_7d_str = f"{change_7d_symbol}{abs(change_7d):.2f}%"

            market_cap_str = "N/A"
            if isinstance(market_cap, (int, float)):
                # Format market cap for readability (e.g., $1.2T, $400.5B, $50.1M)
                if market_cap >= 1e12:
                    market_cap_str = f"${market_cap / 1e12:.1f}T"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap / 1e9:.1f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap / 1e6:.1f}M"
                else:
                     market_cap_str = f"${market_cap:,.0f}"


            report.append(f"| {rank} | {name} ({symbol}) | {price_str} | {change_24h_str} | {change_7d_str} | {market_cap_str} |")

        return "\n".join(report)