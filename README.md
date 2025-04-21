# Financial Newsletter Generator

An automated system that generates and emails a weekly newsletter to investor clients. The newsletter provides timely, insightful updates on the current state of the economy and financial markets, using curated data sources and language generation models.

## Features

- **Automated Data Collection**: Gathers financial and economic data from multiple sources
  - Stock market data (indices, top gainers/losers)
  - Economic indicators (GDP, inflation, unemployment, etc.)
  - Financial news headlines
  
- **AI-Powered Content Generation**: Uses OpenAI's language models to generate:
  - Professional introduction and overview
  - Market analysis with insights
  - Economic analysis and outlook
  - Synthesis of news and data into actionable insights
  
- **Email Distribution System**: Sends newsletters to subscribers
  - Subscriber management (add, remove, list)
  - HTML-formatted emails for professional appearance
  - Support for attachments
  
- **Scheduling**: Automatically runs on a weekly schedule
  - Configurable day and time
  - Minimal human intervention required
  
- **Robust Error Handling**: Comprehensive logging and error recovery

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/bic-42/newsletter-generator.git
   cd financial-newsletter-generator
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the `config` directory based on the provided `.env.example`:
   ```
   cp config/.env.example config/.env
   ```

4. Edit the `.env` file to add your API keys and configuration settings.

## Configuration

The system requires several API keys to function properly:

- **OpenAI API Key**: For generating newsletter content
- **Alpha Vantage API Key**: For economic data
- **FRED API Key**: For additional economic indicators
- **SendGrid API Key**: For sending emails

Additional configuration options in the `.env` file:

- **Email Settings**: Sender email and name
- **Newsletter Settings**: Title, frequency, send day/time
- **Logging Settings**: Log level

## Usage

The system provides a command-line interface with several commands:

### Generate a Newsletter

```
python main.py generate
```

Options:
- `--test`: Run in test mode (doesn't send to all subscribers)
- `--save-only`: Only save the newsletter without sending
- `--recipients`: Specify test recipients (e.g., `--recipients user1@example.com user2@example.com`)

### Schedule Weekly Newsletter

```
python main.py schedule
```

This will start a scheduler that runs the newsletter generation and distribution process on the configured day and time.

### Manage Subscribers

Add a subscriber:
```
python main.py add user@example.com --name "User Name"
```

Remove a subscriber:
```
python main.py remove user@example.com
```

List all subscribers:
```
python main.py list
```

## Project Structure

```
financial-newsletter-generator/
├── config/                  # Configuration files
│   ├── .env.example         # Example environment variables
│   └── subscribers.json     # Subscriber list
├── logs/                    # Log files
├── newsletters/             # Generated newsletters
├── src/                     # Source code
│   ├── data_sources/        # Data collection modules
│   │   ├── base.py          # Base data source class
│   │   ├── stock_market.py  # Stock market data
│   │   ├── economic_indicators.py # Economic data
│   │   └── news_headlines.py # Financial news
│   ├── newsletter_generator/ # Newsletter generation
│   │   └── generator.py     # Main generator class
│   ├── email_service/       # Email distribution
│   │   ├── email_sender.py  # Email sending functionality
│   │   └── subscriber_manager.py # Subscriber management
│   └── config.py            # Configuration loader
├── main.py                  # Main script
└── requirements.txt         # Dependencies
```

## Customization

### Adding New Data Sources

To add a new data source:

1. Create a new class in the `src/data_sources` directory that inherits from `DataSource`
2. Implement the `fetch_data` and `format_data_for_report` methods
3. Add the new data source to the `NewsletterGenerator` class

### Modifying Newsletter Format

The newsletter format can be customized by modifying the `_format_newsletter` method in the `NewsletterGenerator` class.

### Changing Email Templates

Email formatting can be customized in the `_convert_to_html` method of the `NewsletterGenerator` class.

## License

[MIT License](LICENSE)

## Acknowledgements

- [OpenAI](https://openai.com/) for the language model API
- [Alpha Vantage](https://www.alphavantage.co/) for financial data
- [FRED](https://fred.stlouisfed.org/) for economic data
- [SendGrid](https://sendgrid.com/) for email services
- [yfinance](https://github.com/ranaroussi/yfinance) for stock market data