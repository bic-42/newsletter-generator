import openai
from datetime import datetime
# Ensure these imports point to your actual config/data_sources
from ..config import OPENAI_API_KEY, NEWSLETTER_TITLE
from ..data_sources import StockMarketData, EconomicIndicators, NewsHeadlines, CryptoDataSource
import logging
import html # Import for escaping in HTML conversion fallback

logger = logging.getLogger(__name__)

class NewsletterGenerator:
    """
    Generator for financial newsletter content using direct OpenAI API calls.
    Includes both AI-generated analysis and formatted raw data summaries.
    Uses the recommended client pattern for the OpenAI library.
    """

    def __init__(self):
        """Initialize the newsletter generator and OpenAI client."""
        self.client = None
        if not OPENAI_API_KEY:
            logger.error("OpenAI API key is missing. Newsletter generation will fail.")
        else:
            try:
                self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully.")
            except Exception as e:
                 logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)

        # Initialize data sources
        self.stock_data = StockMarketData()
        self.econ_data = EconomicIndicators()
        self.news_data = NewsHeadlines()
        self.crypto_data = CryptoDataSource()
        self.title = NEWSLETTER_TITLE or "Financial Newsletter"

    def _call_openai(self, messages, model: str = "gpt-4-turbo", temperature: float = 0.2, max_tokens: int = 1500) -> str:
        """Helper to call OpenAI ChatCompletion using the client."""
        if not self.client:
             logger.error("OpenAI client not available. Cannot make API call.")
             return "Error: OpenAI client not initialized."
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except openai.AuthenticationError:
            logger.error("OpenAI Authentication Error: Check your API key.")
            return "Error: OpenAI authentication failed."
        except openai.RateLimitError:
             logger.error("OpenAI Rate Limit Error: You have exceeded your quota.")
             return "Error: OpenAI rate limit exceeded."
        except openai.APIConnectionError as e:
             logger.error(f"OpenAI API Connection Error: {e}")
             return "Error: Could not connect to OpenAI API."
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return f"Error: Failed to get response from OpenAI - {e}"

    def generate_newsletter(self) -> dict:
        """Fetch data, generate summaries & analysis, assemble and return newsletter."""
        logger.info("Starting newsletter generation")
        # Fetch raw data
        market = self.stock_data.fetch_data()
        econ = self.econ_data.fetch_data()
        news = self.news_data.fetch_data()
        crypto = self.crypto_data.fetch_data()

        # Check for data fetching errors
        fetch_error = False
        if market.get("error"):
             logger.error(f"Market data fetch error: {market.get('error')}")
             fetch_error = True # Mark as error if core market data fails
        if econ.get("error"):
             logger.warning(f"Economic data fetch error: {econ.get('error')}")
             # Allow continuing, but AI analysis might be affected
        if news.get("error"):
             logger.warning(f"News data fetch error: {news.get('error')}")
             # Allow continuing, but AI analysis might be affected
        if crypto.get("error"):
            logger.warning(f"Crypto data fetch error: {crypto.get('error')}")     


        # --- Generate Formatted Raw Data Summaries ---
        # These methods return pre-formatted markdown strings
        logger.info("Formatting raw market data...")
        formatted_market_summary = self.stock_data.format_data_for_report(market)
        logger.info("Formatting raw economic data...")
        formatted_econ_summary = self.econ_data.format_data_for_report(econ)
        logger.info("Formatting raw news data...")
        formatted_news_summary = self.news_data.format_data_for_report(news)
        logger.info("Formatting raw crypto data...")
        formatted_crypto_summary = self.crypto_data.format_data_for_report(crypto)


        # --- Generate AI Analysis Sections ---
        # Initialize with error messages in case of fetch failure or skipping
        intro = "Introduction could not be generated due to data fetch errors."
        market_analysis = "Market analysis could not be generated due to data fetch errors."
        econ_analysis = "Economic analysis could not be generated due to data fetch errors."
        crypto_analysis = "Crypto analysis could not be generated due to data fetch errors."
        outlook = "Outlook could not be generated due to data fetch errors."

        # Only attempt AI generation if core market data was fetched successfully
        if not fetch_error:
            logger.info("Generating introduction...")
            intro = self._generate_introduction(market)

            logger.info("Generating market analysis...")
            market_analysis = self._generate_market_analysis(market)

            if not econ.get("error"): # Only analyze if econ data is present
                logger.info("Generating economic analysis...")
                econ_analysis = self._generate_economic_analysis(econ)
            else:
                 econ_analysis = "_Economic analysis skipped due to data fetch error._"

            if not crypto.get("error"):
                logger.info("Generating crypto analysis...")
                crypto_analysis = self._generate_crypto_analysis(crypto)
            else:
                crypto_analysis = "Crypto analysis skipped due to data fetch error._"

            # Generate outlook - pass empty news if fetch failed
            logger.info("Generating outlook...")
            current_news_data = news if not news.get("error") else {"all_headlines": []}
            outlook = self._generate_outlook(market, econ, current_news_data, crypto)

            # Basic check if AI generation itself failed
            if "Error:" in intro or "Error:" in market_analysis or "Error:" in econ_analysis or "Error:" in outlook:
                 logger.error("Errors encountered during content generation from OpenAI.")
        else:
             logger.error("Skipping AI generation due to critical data fetch errors.")


        # --- Combine and Format ---
        logger.info("Formatting final newsletter...")
        content = self._format_newsletter(
            # AI Sections
            introduction=intro,
            market_analysis=market_analysis,
            economic_analysis=econ_analysis,
            crypto_analysis=crypto_analysis,
            outlook=outlook,
            # Formatted Raw Data Sections
            formatted_market_summary=formatted_market_summary,
            formatted_econ_summary=formatted_econ_summary,
            formatted_news_summary=formatted_news_summary,
            formatted_crypto_summary=formatted_crypto_summary
        )
        html_content = self._convert_to_html(content)

        logger.info("Newsletter generation process complete.")
        return {
            "title": self.title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "content": content,
            "html_content": html_content,
            "raw_data": {"market": market, "economic": econ, "news": news, "crypto": crypto}
        }

    # --- AI Generation Helper Functions (_generate_introduction, etc.) ---
    def _generate_introduction(self, market_data: dict) -> str:
        today = datetime.now().strftime("%B %d, %Y")
        idx = market_data.get("market_summary", {})
        sp_data = idx.get("^GSPC", {})
        sp = f"{sp_data.get('latest_close', 'N/A'):.2f}" if isinstance(sp_data.get('latest_close'), (int, float)) else "N/A"
        dj_data = idx.get("^DJI", {})
        dj = f"{dj_data.get('latest_close', 'N/A'):.2f}" if isinstance(dj_data.get('latest_close'), (int, float)) else "N/A"
        nq_data = idx.get("^IXIC", {})
        nq = f"{nq_data.get('latest_close', 'N/A'):.2f}" if isinstance(nq_data.get('latest_close'), (int, float)) else "N/A"

        system = "You are a professional financial analyst writing a concise weekly newsletter introduction."
        user = (
            f"Today is {today}.\n"
            f"Current Key Market Levels (for context only, do not repeat in the output): S&P 500: {sp}, Dow Jones: {dj}, NASDAQ Composite: {nq}.\n"
            "Write a 2-paragraph summary of the past week's overall market sentiment and key themes relevant to investors. Focus on tone and broad trends, not specific numbers or detailed analysis."
        )
        return self._call_openai([{"role": "system", "content": system}, {"role": "user", "content": user}])

    def _generate_market_analysis(self, market_data: dict) -> str:
        summary = market_data.get("market_summary", {})
        prompt_summary = ""
        count = 0
        for sym, data in summary.items():
             if data and isinstance(data.get('latest_close'), (int, float)) and count < 4:
                 prompt_summary += f"- {sym}: ~{data['latest_close']:.0f}. "
                 count += 1
        if not prompt_summary: prompt_summary = "Market summary data unavailable."

        system = "You are an insightful financial analyst writing the Market Analysis section of a weekly newsletter."
        user = (
            f"Based on the past week's market action (context: {prompt_summary}), write a 3-paragraph analysis covering the key drivers of overall market performance (positive or negative), notable sector trends (which industries did well or poorly), and any significant technical patterns or market indicators observed. Be specific but maintain a professional tone. Do not simply list the context numbers."
        )
        return self._call_openai([{"role": "system", "content": system}, {"role": "user", "content": user}])
    
    def _generate_crypto_analysis(self, crypto_data: dict) -> str:
        summary = crypto_data.get("crypto_summary", {})
        prompt_summary = ""
        count = 0
        for coin, data in summary.items():
            if data and isinstance(data.get('latest_close'), (int, float)) and count < 4:
                prompt_summary += f"- {coin}: ~{data['latest_close']:.0f}. "
                count += 1
        if not prompt_summary:  prompt_summary = "Crypto summary not available"
        system = "You are an insightful financial analyst writing the Crypto Analysis section of a weekly newsletter."
        user = (
            f"Based on the past week's crypto market action (context: {prompt_summary}), write a 3-paragraph analysis covering the key drivers of overall crypto market performance (positive or negative), notable sector trends (which industries did well or poorly), and any significant technical patterns or crypto market indicators observed. Be specific but maintain a professional tone. Do not simply list the context numbers."
        )
        return self._call_openai([{"role": "system", "content": system}, {"role": "user", "content": user}])

    def _generate_economic_analysis(self, econ_data: dict) -> str:
        items = econ_data.get("economic_summary", {})
        prompt_summary = ""
        count = 0
        key_indicators = ["GDP", "Unemployment Rate", "CPI", "Fed Funds Rate", "Industrial Production"]
        for ind in key_indicators:
             data = items.get(ind)
             if data and isinstance(data.get('latest_value'), (int, float)) and count < 5:
                 unit = "%" if 'Rate' in ind or '%' in ind else ""
                 prompt_summary += f"- {ind}: {data['latest_value']:.1f}{unit}. "
                 count += 1
        if not prompt_summary: prompt_summary = "Key economic indicator data unavailable."

        system = "You are a sharp economist writing the Economic Analysis section of a weekly newsletter."
        user = (
            f"Based on recent key economic indicators (context: {prompt_summary}), write a 3-paragraph analysis discussing the implications for economic growth, inflation trends, the employment situation, and potential impacts on monetary policy (e.g., interest rates). Connect the indicators where possible. Do not simply list the context numbers."
        )
        return self._call_openai([{"role": "system", "content": system}, {"role": "user", "content": user}])

    def _generate_outlook(self, market_data: dict, econ_data: dict, news_data: dict, crypto_data: dict) -> str:
        headlines = news_data.get("all_headlines", [])
        headlines = headlines[:min(len(headlines), 3)]
        news_txt = "\n".join([f"- {h['headline']}" for h in headlines if h and 'headline' in h]) if headlines else "No recent headlines available for context."

        top_stocks = market_data.get("top_stocks", [])
        market_context = ""
        if top_stocks:
            top_performer = max(top_stocks, key=lambda x: x.get('daily_change_pct') or -float('inf'))
            worst_performer = min(top_stocks, key=lambda x: x.get('daily_change_pct') or float('inf'))
            market_context = f"Top market mover (24h): {top_performer.get('name')} ({top_performer.get('daily_change_pct', 0):.1f}%). "
            market_context += f"Bottom crypto mover (24h): {worst_performer.get('name')} ({worst_performer.get('daily_change_pct', 0):.1f}%)."

        # Brief crypto context if available
        top_cryptos = crypto_data.get("top_cryptos", [])
        crypto_context = ""
        if top_cryptos:
             top_performer = max(top_cryptos, key=lambda x: x.get('daily_change_pct') or -float('inf'))
             worst_performer = min(top_cryptos, key=lambda x: x.get('daily_change_pct') or float('inf'))
             crypto_context = f"Top crypto mover (24h): {top_performer.get('name')} ({top_performer.get('daily_change_pct', 0):.1f}%). "
             crypto_context += f"Bottom crypto mover (24h): {worst_performer.get('name')} ({worst_performer.get('daily_change_pct', 0):.1f}%)."

        

        system = "You are an experienced financial strategist writing the Outlook section for a weekly newsletter."
        user = (
            f"Considering the market action and economic data analyzed previously, plus these recent key news headlines (for context only):\n{news_txt}\n\n"
            f"Also note recent crypto action (for context only): {crypto_context}\n\n"
            "Write a 3-paragraph forward-looking outlook for investors. Discuss potential risks on the horizon and identify possible opportunities or areas to watch in the coming week(s). Be balanced and avoid making definitive predictions."
        )
        return self._call_openai([{"role": "system", "content": system}, {"role": "user", "content": user}])

    # --- Formatting Function ---

    def _format_newsletter(self, **sections) -> str:
        """Combine AI sections and formatted raw data into final markdown newsletter."""

        md_content = [f"# {self.title}", f"**{datetime.now().strftime('%B %d, %Y')}**"]

        # --- Section 1: Introduction (AI) ---
        intro_text = sections.get('introduction', '_Introduction could not be generated._')
        if intro_text and "Error:" not in intro_text:
            md_content.append("## Introduction")
            md_content.append(intro_text)
        else:
             md_content.append("## Introduction")
             md_content.append(f"_{intro_text}_") # Show error if exists

        # --- Section 2: Market Analysis (AI) ---
        market_analysis_text = sections.get('market_analysis', '_Market analysis could not be generated._')
        if market_analysis_text and "Error:" not in market_analysis_text:
            md_content.append("## Market Analysis")
            md_content.append(market_analysis_text)
        else:
             md_content.append("## Market Analysis")
             md_content.append(f"_{market_analysis_text}_")

        # --- Section 3: Market Data Summary (Raw Formatted) ---
        # This assumes formatted_market_summary starts with "# Market Summary" or similar
        market_summary_raw = sections.get('formatted_market_summary', '_Market data summary unavailable._')
        # We add it directly as it should contain its own top-level title from its formatter
        md_content.append(market_summary_raw)

        # --- Section 4: Economic Analysis (AI) ---
        econ_analysis_text = sections.get('economic_analysis', '_Economic analysis could not be generated._')
        if econ_analysis_text and "Error:" not in econ_analysis_text and "skipped" not in econ_analysis_text:
            md_content.append("## Economic Analysis")
            md_content.append(econ_analysis_text)
        else:
             md_content.append("## Economic Analysis")
             md_content.append(f"_{econ_analysis_text}_")

        # --- Section 5: Economic Indicators (Raw Formatted) ---
        # Assumes formatted_econ_summary starts with "# Economic Indicators"
        econ_summary_raw = sections.get('formatted_econ_summary', '_Economic indicators data unavailable._')
        md_content.append(econ_summary_raw)

        # --- Section 6: Crypto Data Summary (Raw Formatted) ---
        crypto_summary_raw = sections.get('formatted_crypto_summary', '_crypto data summary unavailable_')
        md_content.append(crypto_summary_raw)

        # --- Section 7: Crypto Analysis (AI) ---
        crypto_analysis_text = sections.get('crypto_analysis', '_Crypto analysis could not be generated._')
        if crypto_analysis_text and "Error:" not in crypto_analysis_text and "skipped" not in crypto_analysis_text:
            md_content.append("## Crypto Analysis")
            md_content.append(crypto_analysis_text)
        else:
            md_content.append("## Crypto Analysis")
            md_content.append(f"_{crypto_analysis_text}_")    

        # --- Section 8: Recent News (Raw Formatted) ---
        # Assumes formatted_news_summary starts with "# Financial News Headlines"
        news_summary_raw = sections.get('formatted_news_summary', '_News headlines unavailable._')
        md_content.append(news_summary_raw)

        # --- Section 9: Outlook (AI) ---
        outlook_text = sections.get('outlook', '_Outlook could not be generated._')
        if outlook_text and "Error:" not in outlook_text:
            md_content.append("## Outlook")
            md_content.append(outlook_text)
        else:
             md_content.append("## Outlook")
             md_content.append(f"_{outlook_text}_")

        # --- Footer ---
        footer = f"\n---\n*Disclaimer: This newsletter is for informational purposes only and does not constitute financial advice. Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        md_content.append(footer)

        # Join all parts with double newlines for markdown paragraphs/spacing
        return "\n\n".join(md_content)

    def _convert_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML using the markdown library with styling."""
        try:
            import markdown
            # Use extensions for better formatting like tables, fenced code, line breaks
            html_body = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'nl2br'])
        except ImportError:
            logger.warning("markdown library not found, using basic conversion.")
            # Basic HTML escaping for safety
            escaped_content = html.escape(markdown_content)
            # Simple replacements for basic markdown structure
            # This fallback is very basic and might not look great
            html_body = escaped_content.replace('\n\n', '</p><p>')
            html_body = html_body.replace('\n* ', '</li><li>').replace('\n- ', '</li><li>')
            if '<li>' in html_body: html_body = f"<ul><li>{html_body.split('<li>', 1)[1]}</li></ul>" # Basic list wrapping
            html_body = html_body.replace('# ', '<h1>').replace('## ', '<h2>').replace('### ', '<h3>')
            html_body = f"<p>{html_body}</p>" # Wrap loose text

        # Add CSS styling wrapper
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.title}</title>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 20px auto; padding: 15px; border: 1px solid #eee; }}
                h1, h2, h3 {{ color: #2c3e50; margin-top: 1.5em; margin-bottom: 0.5em; }}
                h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 0.3em; font-size: 1.8em; }}
                h2 {{ border-bottom: 1px solid #eee; padding-bottom: 0.2em; font-size: 1.4em; }}
                h3 {{ font-size: 1.1em; color: #34495e; }}
                p {{ margin-bottom: 1em; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                ul {{ padding-left: 20px; list-style-type: disc; }} /* Ensure list styling */
                li {{ margin-bottom: 0.5em; }}
                code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
                pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                .footer {{ margin-top: 2em; padding-top: 1em; border-top: 1px solid #eee; font-size: 0.85em; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """
        return styled_html