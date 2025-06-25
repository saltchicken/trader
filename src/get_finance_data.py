import finnhub
import yfinance as yf
import json
import time
import threading
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("FINNHUB_API_KEY")
if not API_KEY:
    raise ValueError("Missing FINNHUB_API_KEY in .env")

client = finnhub.Client(api_key=API_KEY)

class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, func):
        def wrapped(*args, **kwargs):
            with self.lock:
                now = time.time()
                # Remove calls older than period
                self.calls = [t for t in self.calls if now - t < self.period]
                if len(self.calls) >= self.max_calls:
                    sleep_time = self.period - (now - self.calls[0])
                    time.sleep(sleep_time)
                self.calls.append(time.time())
            return func(*args, **kwargs)
        return wrapped

# Allow 60 calls per 60 seconds
rate_limit = RateLimiter(max_calls=60, period=60)

@rate_limit
def get_profile(symbol):
    return client.company_profile2(symbol=symbol)

@rate_limit
def print_profile(symbol):
    profile = get_profile(symbol)
    print(json.dumps(profile, indent=4))

@rate_limit
def get_current_quote(symbol):
    return client.quote(symbol)

@rate_limit
def print_current_quote(symbol):
    quote = get_current_quote(symbol)
    print(json.dumps(quote, indent=4))

@rate_limit
def get_financials(symbol):
    return client.financials_reported(symbol=symbol)

@rate_limit
def print_financials(symbol):
    financials = get_financials(symbol)
    print(json.dumps(financials, indent=4))

@rate_limit
def get_metrics(symbol):
    return client.company_basic_financials(symbol=symbol, metric="all")

@rate_limit
def print_metrics(symbol):
    metrics = get_metrics(symbol)
    print(json.dumps(metrics, indent=4))

@rate_limit
def get_filings(symbol, _from, to):
    return client.filings(symbol=symbol, _from=_from, to=to)

@rate_limit
def print_filings(symbol):
    filings = get_filings(symbol, _from="2025-01-01", to="2025-06-24")
    print(json.dumps(filings, indent=4))

@rate_limit
def get_quote_history(symbol, period="1y"):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period)
    return data

if __name__ == "__main__":
    print_profile("AAPL")
