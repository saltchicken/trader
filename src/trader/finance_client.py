import finnhub
import pandas as pd
import time
import threading
from dotenv import load_dotenv
import os
from datetime import datetime

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError

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

    @RateLimiter(1, 1.25)
    def get_profile(self, symbol):
        return self.client.company_profile2(symbol=symbol)

    @RateLimiter(1, 1.25)
    def get_financials(self, symbol):
        return self.client.financials_reported(symbol=symbol)

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
        return df_filtered[["symbol", "description"]].to_dict(orient="records")
        # return df_filtered["symbol"].tolist()
        #

    def get_all_stock_data(self, symbols, days_back=730):
        """Download stock data for multiple symbols using a single Alpaca API call"""
        try:
            print(
                f"📥 Downloading data for {symbols} from Alpaca in single API call..."
            )

            # Initialize the client
            client = StockHistoricalDataClient(
                api_key=os.getenv("APCA_API_KEY_ID"),
                secret_key=os.getenv("APCA_API_SECRET_KEY"),
            )

            # Calculate start and end dates
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=days_back)

            # Create request for daily bars for all symbols at once
            request_params = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
            )

            # Get the data for all symbols
            bars = client.get_stock_bars(request_params)

            if not bars.data:
                raise ValueError("No data found for any symbols")

            # Convert to dictionary of DataFrames
            stock_data = {}

            for symbol in symbols:
                if symbol not in bars.data:
                    print(f"⚠️ No data found for symbol {symbol}")
                    stock_data[symbol] = None
                    continue

                # Convert to DataFrame
                data_list = []
                for bar in bars.data[symbol]:
                    data_list.append(
                        {
                            "timestamp": bar.timestamp,
                            "Open": float(bar.open),
                            "High": float(bar.high),
                            "Low": float(bar.low),
                            "Close": float(bar.close),
                            "Volume": int(bar.volume),
                        }
                    )

                data = pd.DataFrame(data_list)
                data.set_index("timestamp", inplace=True)

                # Ensure we have the required columns
                required_columns = ["Open", "High", "Low", "Close", "Volume"]
                missing_columns = [
                    col for col in required_columns if col not in data.columns
                ]
                if missing_columns:
                    print(f"⚠️ Missing required columns for {symbol}: {missing_columns}")
                    stock_data[symbol] = None
                    continue

                # Remove any rows with NaN values or zero volume
                data = data.dropna()
                data = data[data["Volume"] > 0]

                # Add VWAP calculation
                data["VWAP"] = (
                    data["Volume"] * (data["High"] + data["Low"] + data["Close"]) / 3
                ).cumsum() / data["Volume"].cumsum()

                data["CUSTOM"] = [None] * len(data)

                if len(data) < 50:  # Need minimum data for analysis
                    print(f"⚠️ Insufficient data for {symbol}: only {len(data)} rows")
                    stock_data[symbol] = None
                    continue

                print(f"✅ Downloaded {len(data)} rows of data for {symbol}")
                stock_data[symbol] = data

            return stock_data

        except APIError as e:
            print(f"❌ Alpaca API Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error downloading data: {e}")
            return None


# === Example Usage ===
if __name__ == "__main__":
    fh = FinanceClient()
    data = fh.get_quote_history("AAPL")
    print(data)
