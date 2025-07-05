from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError
from dotenv import load_dotenv
import pandas as pd
import os
import datetime

load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
if not API_KEY or not SECRET_KEY:
    raise ValueError("Missing APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env")


class AlpacaClient:
    def __init__(self):
        self.client = StockHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

    def get_all_stock_data(self, symbols, days_back=730):
        """Download stock data for multiple symbols using a single Alpaca API call"""
        try:
            print(
                f"📥 Downloading data for {symbols} from Alpaca in single API call..."
            )

            # Initialize the client

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
            bars = self.client.get_stock_bars(request_params)

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
