"""
Module for generating newsletter content using language models.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import openai
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from ..config import OPENAI_API_KEY, NEWSLETTER_TITLE
from config.logger import logger
from ..data_sources import StockMarketData, EconomicIndicators, NewsHeadlines

class NewsletterGenerator:
    """
    Generator for financial newsletter content.

    Uses data from various sources and language models to generate a complete newsletter.
    """

    def __init__(self):
        """Initialize the newsletter generator."""
        self.logger = logger.getChild(self.__class__.__name__)

        # Set OpenAI API key
        if not OPENAI_API_KEY:
            self.logger.error("OpenAI API key is missing. Newsletter generation will fail.")
        else:
            openai.api_key = OPENAI_API_KEY

        # Initialize data sources
        self.stock_market = StockMarketData()
        self.economic_indicators = EconomicIndicators()
        self.news_headlines = NewsHeadlines()

        # Newsletter title
        self.title = NEWSLETTER_TITLE

    def generate_newsletter(self) -> Dict[str, Any]:
        """
        Generate a complete newsletter.

        Returns:
            Dictionary containing the newsletter content and metadata
        """
        self.logger.info("Starting newsletter generation")

        try:
            # Fetch data from all sources
            market_data = self.stock_market.fetch_data()
            economic_data = self.economic_indicators.fetch_data()
            news_data = self.news_headlines.fetch_data()

            # Generate newsletter sections
            introduction = self._generate_introduction(market_data, economic_data)
            market_summary = self.stock_market.format_data_for_report(market_data)
            economic_summary = self.economic_indicators.format_data_for_report(economic_data)
            news_summary = self.news_headlines.format_data_for_report(news_data)

            # Generate analysis and insights
            market_analysis = self._generate_market_analysis(market_data)
            economic_analysis = self._generate_economic_analysis(economic_data)
            outlook = self._generate_outlook(market_data, economic_data, news_data)

            # Combine all sections
            content = self._format_newsletter(
                introduction=introduction,
                market_summary=market_summary,
                market_analysis=market_analysis,
                economic_summary=economic_summary,
                economic_analysis=economic_analysis,
                news_summary=news_summary,
                outlook=outlook
            )

            # Create newsletter object
            newsletter = {
                "title": self.title,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "content": content,
                "html_content": self._convert_to_html(content),
                "raw_data": {
                    "market_data": market_data,
                    "economic_data": economic_data,
                    "news_data": news_data
                }
            }

            self.logger.info("Newsletter generation completed successfully")
            return newsletter

        except Exception as e:
            self.logger.error(f"Error generating newsletter: {str(e)}")
            # Return a minimal newsletter with error information
            return {
                "title": self.title,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "content": f"# Error Generating Newsletter\n\nThere was an error generating this week's newsletter: {str(e)}",
                "html_content": f"<h1>Error Generating Newsletter</h1><p>There was an error generating this week's newsletter: {str(e)}</p>",
                "error": str(e)
            }

    def _generate_introduction(self, market_data: Dict[str, Any], economic_data: Dict[str, Any]) -> str:
        """
        Generate an introduction for the newsletter.

        Args:
            market_data: Stock market data
            economic_data: Economic indicator data

        Returns:
            Formatted introduction text
        """
        self.logger.info("Generating newsletter introduction")

        try:
            # Extract key market metrics for the prompt
            market_summary = market_data.get("market_summary", {})
            sp500_data = market_summary.get("^GSPC", {})
            dow_data = market_summary.get("^DJI", {})
            nasdaq_data = market_summary.get("^IXIC", {})

            # Extract key economic indicators
            economic_summary = economic_data.get("economic_summary", {})

            # Create a prompt for the language model
            prompt = PromptTemplate(
                input_variables=["date", "sp500", "dow", "nasdaq"],
                template="""
                You are a professional financial analyst writing the introduction to a weekly newsletter for investors.
                Today is {date}.

                Key market indicators:
                - S&P 500: {sp500}
                - Dow Jones: {dow}
                - NASDAQ: {nasdaq}

                Write a professional, insightful introduction (2-3 paragraphs) for this week's financial newsletter.
                Focus on the overall market sentiment and key themes for investors to watch.
                Use a professional, confident tone that would be appropriate for sophisticated investors.
                Do not include specific numbers in your response, just provide a high-level overview.
                """
            )

            # Format the S&P 500 data for the prompt
            sp500_text = "data not available"
            if sp500_data:
                change = sp500_data.get("daily_change_pct")
                direction = "up" if change and change > 0 else "down"
                sp500_text = f"{sp500_data.get('latest_close', 'N/A'):.2f}, {direction} {abs(change):.2f}% this week" if change else "data incomplete"

            # Format the Dow data for the prompt
            dow_text = "data not available"
            if dow_data:
                change = dow_data.get("daily_change_pct")
                direction = "up" if change and change > 0 else "down"
                dow_text = f"{dow_data.get('latest_close', 'N/A'):.2f}, {direction} {abs(change):.2f}% this week" if change else "data incomplete"

            # Format the NASDAQ data for the prompt
            nasdaq_text = "data not available"
            if nasdaq_data:
                change = nasdaq_data.get("daily_change_pct")
                direction = "up" if change and change > 0 else "down"
                nasdaq_text = f"{nasdaq_data.get('latest_close', 'N/A'):.2f}, {direction} {abs(change):.2f}% this week" if change else "data incomplete"

            # Create the chain
            llm = OpenAI(temperature=0.7)
            chain = LLMChain(llm=llm, prompt=prompt)

            # Run the chain
            introduction = chain.run(
                date=datetime.now().strftime("%B %d, %Y"),
                sp500=sp500_text,
                dow=dow_text,
                nasdaq=nasdaq_text
            )

            # Format the introduction
            formatted_intro = f"# {self.title}\n\n**{datetime.now().strftime('%B %d, %Y')}**\n\n{introduction.strip()}\n\n"

            return formatted_intro

        except Exception as e:
            self.logger.error(f"Error generating introduction: {str(e)}")
            return f"# {self.title}\n\n**{datetime.now().strftime('%B %d, %Y')}**\n\nWelcome to this week's financial newsletter.\n\n"

    def _generate_market_analysis(self, market_data: Dict[str, Any]) -> str:
        """
        Generate market analysis using language models.

        Args:
            market_data: Stock market data

        Returns:
            Formatted market analysis text
        """
        self.logger.info("Generating market analysis")

        try:
            # Extract relevant data for the prompt
            market_summary = market_data.get("market_summary", {})
            stock_performance = market_data.get("stock_performance", {})

            # Create a prompt for the language model
            prompt = PromptTemplate(
                input_variables=["market_data", "top_gainers", "top_losers"],
                template="""
                You are a professional financial analyst providing market analysis for a weekly investor newsletter.

                Market data:
                {market_data}

                Top performing stocks:
                {top_gainers}

                Underperforming stocks:
                {top_losers}

                Based on this data, write a detailed market analysis (3-4 paragraphs) that explains:
                1. The overall market performance and key trends
                2. Sector-specific insights
                3. What might be driving the performance of top gainers and losers
                4. Technical indicators or patterns worth noting

                Use a professional, analytical tone. Provide specific insights that would be valuable to investors.
                """
            )

            # Format market data for the prompt
            market_data_text = ""
            for index, data in market_summary.items():
                index_name = self.stock_market._get_index_name(index)
                change = data.get("daily_change_pct")
                direction = "up" if change and change > 0 else "down"
                change_text = f"{direction} {abs(change):.2f}%" if change is not None else "unchanged"
                market_data_text += f"- {index_name}: {data.get('latest_close', 'N/A'):.2f}, {change_text}\n"

            # Format top gainers for the prompt
            top_gainers_text = ""
            for ticker, data in stock_performance.get("top_gainers", {}).items():
                change = data.get("daily_change_pct")
                top_gainers_text += f"- {ticker}: ${data.get('latest_close', 'N/A'):.2f}, up {change:.2f}%\n" if change else f"- {ticker}: data incomplete\n"

            # Format top losers for the prompt
            top_losers_text = ""
            for ticker, data in stock_performance.get("top_losers", {}).items():
                change = data.get("daily_change_pct")
                top_losers_text += f"- {ticker}: ${data.get('latest_close', 'N/A'):.2f}, down {abs(change):.2f}%\n" if change else f"- {ticker}: data incomplete\n"

            # Create the chain
            llm = OpenAI(temperature=0.7)
            chain = LLMChain(llm=llm, prompt=prompt)

            # Run the chain
            analysis = chain.run(
                market_data=market_data_text,
                top_gainers=top_gainers_text,
                top_losers=top_losers_text
            )

            # Format the analysis
            formatted_analysis = f"## Market Analysis\n\n{analysis.strip()}\n\n"

            return formatted_analysis

        except Exception as e:
            self.logger.error(f"Error generating market analysis: {str(e)}")
            return "## Market Analysis\n\nAnalysis could not be generated due to an error.\n\n"

    def _generate_economic_analysis(self, economic_data: Dict[str, Any]) -> str:
        """
        Generate economic analysis using language models.

        Args:
            economic_data: Economic indicator data

        Returns:
            Formatted economic analysis text
        """
        self.logger.info("Generating economic analysis")

        try:
            # Extract relevant data for the prompt
            economic_summary = economic_data.get("economic_summary", {})

            # Create a prompt for the language model
            prompt = PromptTemplate(
                input_variables=["economic_indicators"],
                template="""
                You are a professional economist providing analysis for a weekly investor newsletter.

                Economic indicators:
                {economic_indicators}

                Based on these indicators, write a detailed economic analysis (3-4 paragraphs) that explains:
                1. The current state of the economy
                2. Trends in inflation, employment, and growth
                3. Potential implications for monetary policy
                4. How these economic conditions might affect different market sectors

                Use a professional, analytical tone. Provide specific insights that would be valuable to investors.
                """
            )

            # Format economic data for the prompt
            economic_indicators_text = ""
            for indicator, data in economic_summary.items():
                value = data.get("latest_value")
                date = data.get("latest_date", "N/A")
                change = data.get("change_pct")

                # Format the value based on the indicator
                value_str = f"{value:.2f}"
                if "Rate" in indicator or "Unemployment" in indicator:
                    value_str = f"{value:.2f}%"

                # Format the change
                change_str = ""
                if change is not None:
                    direction = "up" if change > 0 else "down"
                    change_str = f", {direction} {abs(change):.2f}%"

                economic_indicators_text += f"- {indicator}: {value_str}{change_str} (as of {date})\n"

            # Create the chain
            llm = OpenAI(temperature=0.7)
            chain = LLMChain(llm=llm, prompt=prompt)

            # Run the chain
            analysis = chain.run(economic_indicators=economic_indicators_text)

            # Format the analysis
            formatted_analysis = f"## Economic Analysis\n\n{analysis.strip()}\n\n"

            return formatted_analysis

        except Exception as e:
            self.logger.error(f"Error generating economic analysis: {str(e)}")
            return "## Economic Analysis\n\nAnalysis could not be generated due to an error.\n\n"

    def _generate_outlook(self, market_data: Dict[str, Any], economic_data: Dict[str, Any], news_data: Dict[str, Any]) -> str:
        """
        Generate market outlook using language models.

        Args:
            market_data: Stock market data
            economic_data: Economic indicator data
            news_data: News headline data

        Returns:
            Formatted outlook text
        """
        self.logger.info("Generating market outlook")

        try:
            # Extract relevant data for the prompt
            market_summary = market_data.get("market_summary", {})
            economic_summary = economic_data.get("economic_summary", {})
            headlines = news_data.get("all_headlines", [])

            # Create a prompt for the language model
            prompt = PromptTemplate(
                input_variables=["market_data", "economic_data", "headlines"],
                template="""
                You are a professional financial strategist providing a forward-looking outlook for a weekly investor newsletter.

                Market data:
                {market_data}

                Economic indicators:
                {economic_data}

                Recent headlines:
                {headlines}

                Based on this information, write a comprehensive outlook (3-4 paragraphs) that:
                1. Synthesizes the market and economic data to provide a forward-looking perspective
                2. Identifies key risks and opportunities for investors in the coming weeks
                3. Suggests potential investment strategies or sectors to watch
                4. Considers how recent news might impact market sentiment

                Use a professional, strategic tone. Provide specific, actionable insights that would be valuable to investors.
                """
            )

            # Format market data for the prompt
            market_data_text = ""
            for index, data in market_summary.items():
                index_name = self.stock_market._get_index_name(index)
                change = data.get("daily_change_pct")
                direction = "up" if change and change > 0 else "down"
                change_text = f"{direction} {abs(change):.2f}%" if change is not None else "unchanged"
                market_data_text += f"- {index_name}: {data.get('latest_close', 'N/A'):.2f}, {change_text}\n"

            # Format economic data for the prompt
            economic_data_text = ""
            key_indicators = ["GDP", "Unemployment Rate", "CPI", "Fed Funds Rate"]
            for indicator in key_indicators:
                if indicator in economic_summary:
                    data = economic_summary[indicator]
                    value = data.get("latest_value")
                    change = data.get("change_pct")

                    # Format the value based on the indicator
                    value_str = f"{value:.2f}"
                    if "Rate" in indicator or "Unemployment" in indicator:
                        value_str = f"{value:.2f}%"

                    # Format the change
                    change_str = ""
                    if change is not None:
                        direction = "up" if change > 0 else "down"
                        change_str = f", {direction} {abs(change):.2f}%"

                    economic_data_text += f"- {indicator}: {value_str}{change_str}\n"

            # Format headlines for the prompt
            headlines_text = ""
            for i, headline in enumerate(headlines[:5]):  # Use top 5 headlines
                headlines_text += f"- {headline.get('headline')}\n"

            # Create the chain
            llm = OpenAI(temperature=0.7)
            chain = LLMChain(llm=llm, prompt=prompt)

            # Run the chain
            outlook = chain.run(
                market_data=market_data_text,
                economic_data=economic_data_text,
                headlines=headlines_text
            )

            # Format the outlook
            formatted_outlook = f"## Market Outlook\n\n{outlook.strip()}\n\n"

            return formatted_outlook

        except Exception as e:
            self.logger.error(f"Error generating outlook: {str(e)}")
            return "## Market Outlook\n\nOutlook could not be generated due to an error.\n\n"

    def _format_newsletter(self, **sections) -> str:
        """
        Format the complete newsletter.

        Args:
            **sections: Newsletter sections

        Returns:
            Formatted newsletter content
        """
        # Order of sections
        section_order = [
            "introduction",
            "market_summary",
            "market_analysis",
            "economic_summary",
            "economic_analysis",
            "news_summary",
            "outlook"
        ]

        # Combine sections in order
        content = []
        for section in section_order:
            if section in sections and sections[section]:
                content.append(sections[section])

        # Add footer
        footer = f"\n\n---\n\n*This newsletter was automatically generated on {datetime.now().strftime('%Y-%m-%d')}.*"
        content.append(footer)

        return "\n".join(content)

    def _convert_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown content to HTML.

        Args:
            markdown_content: Newsletter content in markdown format

        Returns:
            HTML formatted newsletter
        """
        try:
            # Try to import markdown
            import markdown

            # Convert markdown to HTML
            html = markdown.markdown(markdown_content)

            # Add basic styling
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{self.title}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1, h2, h3 {{
                        color: #2c3e50;
                    }}
                    h1 {{
                        border-bottom: 2px solid #eee;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        border-bottom: 1px solid #eee;
                        padding-bottom: 5px;
                        margin-top: 30px;
                    }}
                    a {{
                        color: #3498db;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    .footer {{
                        margin-top: 40px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        font-size: 0.8em;
                        color: #7f8c8d;
                    }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """

            return styled_html

        except ImportError:
            self.logger.warning("Markdown module not found. Returning plain HTML.")

            # Simple markdown to HTML conversion for basic elements
            html = markdown_content
            html = html.replace("# ", "<h1>").replace("\n## ", "</h1>\n<h2>").replace("\n### ", "</h2>\n<h3>")
            html = html.replace("\n\n", "</p><p>")
            html = f"<p>{html}</p>"
            html = html.replace("</h1>\n<p>", "</h1><p>").replace("</h2>\n<p>", "</h2><p>").replace("</h3>\n<p>", "</h3><p>")

            return f"<html><body>{html}</body></html>"
