import finnhub
import yfinance as yf
import pandas as pd
import json
import time
import threading
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.getenv("FINNHUB_API_KEY")
if not API_KEY:
    raise ValueError("Missing FINNHUB_API_KEY in .env")


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
                self.calls = [t for t in self.calls if now - t < self.period]
                if len(self.calls) >= self.max_calls:
                    sleep_time = self.period - (now - self.calls[0])
                    print(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
                    time.sleep(sleep_time)
                self.calls.append(time.time())
            return func(*args, **kwargs)

        return wrapped


class FinanceClient:
    def __init__(self, api_key=API_KEY, max_calls_per_minute=60):
        self.client = finnhub.Client(api_key=api_key)
        self.rate_limit = RateLimiter(max_calls_per_minute, 60)

    @property
    def limit(self):
        return self.rate_limit

    @RateLimiter(60, 60)
    def get_profile(self, symbol):
        return self.client.company_profile2(symbol=symbol)

    def print_profile(self, symbol):
        print(json.dumps(self.get_profile(symbol), indent=4))

    @RateLimiter(60, 60)
    def get_current_quote(self, symbol):
        return self.client.quote(symbol)

    def print_current_quote(self, symbol):
        print(json.dumps(self.get_current_quote(symbol), indent=4))

    @RateLimiter(60, 60)
    def get_financials(self, symbol):
        return self.client.financials_reported(symbol=symbol)

    def print_financials(self, symbol):
        print(json.dumps(self.get_financials(symbol), indent=4))

    @RateLimiter(60, 60)
    def get_metrics(self, symbol):
        return self.client.company_basic_financials(symbol=symbol, metric="all")

    def print_metrics(self, symbol):
        print(json.dumps(self.get_metrics(symbol), indent=4))

    @RateLimiter(60, 60)
    def get_filings(self, symbol, _from, to):
        return self.client.filings(symbol=symbol, _from=_from, to=to)

    def print_filings(self, symbol, _from="2025-01-01", to="2025-06-24"):
        print(json.dumps(self.get_filings(symbol, _from, to), indent=4))

    @RateLimiter(60, 60)
    def get_quote_history(self, symbol, period="1y"):
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data

    @RateLimiter(60, 60)
    def get_revenue_per_share_history(self, symbol):
        ticker = yf.Ticker(symbol)
        income_stmt = ticker.financials.T  # Income statement: Total Revenue
        balance_sheet = (
            ticker.balance_sheet.T
        )  # Balance sheet: Common Shares Outstanding
        if "Total Revenue" not in income_stmt.columns or "Ordinary Shares Number" not in balance_sheet.columns:
            return None
        df = pd.concat(
            [income_stmt["Total Revenue"], balance_sheet["Ordinary Shares Number"]],
            axis=1,
        )

        # Rename columns
        df.columns = ["Total Revenue", "Shares Outstanding"]
        df["Year"] = df.index.year if isinstance(df.index[0], pd.Timestamp) else df.index.astype(str).str[:4]

        # Calculate Revenue per Share
        df["Revenue Per Share"] = np.where(df["Shares Outstanding"] != 0, df["Total Revenue"] / df["Shares Outstanding"], np.nan)
        df.dropna(inplace=True)

        # Display with most recent first
        result = df.to_dict(orient="records")
        return result
        # return df[["Revenue Per Share"]]


# === Example Usage ===
if __name__ == "__main__":
    fh = FinanceClient()
    data = fh.get_quote_history("AAPL")
    print(data)
