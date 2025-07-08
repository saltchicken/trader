import finnhub
import pandas as pd
import time
import threading
from dotenv import load_dotenv
import os

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


class FinnHubClient:
    def __init__(self, api_key=API_KEY, max_calls_per_minute=60):
        self.client = finnhub.Client(api_key=api_key)
        self.rate_limit = RateLimiter(max_calls_per_minute, 60)

    @property
    def limit(self):
        return self.rate_limit

    @RateLimiter(1, 1.25)
    def get_profile(self, symbol):
        return self.client.company_profile2(symbol=symbol)

    @RateLimiter(1, 1.25)
    def get_financials(self, symbol):
        try:
            financials_reported = self.client.financials_reported(
                symbol=symbol, freq="quarterly"
            )
        except Exception:
            return False
        return financials_reported

    @RateLimiter(1, 1.25)
    def get_metrics(self, symbol):
        try:
            metrics = self.client.company_basic_financials(symbol=symbol, metric="all")
            return metrics
        except Exception:
            return False

    @RateLimiter(1, 1.25)
    def get_filings(self, symbol, _from, to):
        return self.client.filings(symbol=symbol, _from=_from, to=to)

    def get_all_stocks(self):
        symbols = self.client.stock_symbols("US")
        df = pd.DataFrame(symbols)
        valid_mics = ["XNYS", "XNAS"]  # NYSE and NASDAQ

        df_filtered = df[(df["type"] == "Common Stock") & (df["mic"].isin(valid_mics))]
        # df_filtered = df_filtered[~df_filtered["symbol"].str.contains(r"\.")]

        # print(f"Filtered count: {len(df_filtered)}")
        symbols = df_filtered["symbol"].to_list()
        for symbol in symbols:
            profile = self.get_profile(symbol)
            print("dljalskdjf")
            print(profile)
            print("akjsldfjkaslkdjf")
            if profile and "name" in profile:
                df_filtered.loc[df_filtered["symbol"] == symbol, "sector"] = profile[
                    "finnhubIndustry"
                ]
                df_filtered.loc[df_filtered["symbol"] == symbol, "ipo"] = profile["ipo"]
                df_filtered.loc[df_filtered["symbol"] == symbol, "weburl"] = profile[
                    "weburl"
                ]
                print(df_filtered)

        return df_filtered[
            ["symbol", "description", "ipo", "weburl", "sector"]
        ].to_dict(orient="records")
        # return df_filtered["symbol"].tolist()
        #


# === Example Usage ===
if __name__ == "__main__":
    fh = FinanceClient()
    data = fh.get_quote_history("AAPL")
    print(data)
