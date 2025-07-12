# Trader

This project is a trading bot that uses various financial data sources to make trading decisions.

## Features

*   Connects to Alpaca and Finnhub for real-time market data and trading.
*   Uses technical analysis (TA) and backtesting to evaluate trading strategies.
*   Parses SEC filings from Edgar to gather fundamental data.
*   Logs trading activity using Loguru.
*   Manages configuration using environment variables.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/saltchicken/trader.git
    ```
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up your environment variables by creating a `.env` file in the root directory. See the `.env.example` file for a list of required variables.

## Usage

To run the trading bot, use the following command:

```bash
trader
```

## Dependencies

*   [finnhub-python](https://github.com/Finnhub-Stock-API/finnhub-python)
*   [matplotlib](https://matplotlib.org/)
*   [numpy](https://numpy.org/)
*   [pandas](https://pandas.pydata.org/)
*   [ta](https://github.com/bukosabino/ta)
*   [python-dotenv](https://github.com/theskumar/python-dotenv)
*   [SQLAlchemy](https://www.sqlalchemy.org/)
*   [lxml](https://lxml.de/)
*   [loguru](https://github.com/Delgan/loguru)
*   [alpaca-py](https://github.com/alpacahq/alpaca-py)
*   [edgartools](https://pypi.org/project/edgartools/)
*   [backtesting](https://github.com/kernc/backtesting.py)
*   [psycopg2-binary](https://pypi.org/project/psycopg2-binary/)
