from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient

from alpaca.data.requests import (
    StockQuotesRequest,
)
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
    TrailingStopOrderRequest,
)
from alpaca.trading.enums import (
    OrderClass,
    OrderSide,
    QueryOrderStatus,
    TimeInForce,
)
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
    def __init__(self, paper=True):
        self.historical_client = StockHistoricalDataClient(
            api_key=API_KEY, secret_key=SECRET_KEY
        )
        self.trading_client = TradingClient(API_KEY, SECRET_KEY, paper=paper)
        self.acct = self.trading_client.get_account()
        self.acct_config = self.trading_client.get_account_configurations()
        # self.assets = self.trading_client.get_all_assets(
        #     GetAssetsRequest(status=AssetStatus.ACTIVE)
        # )
        self.orders = self.trading_client.get_orders(
            GetOrdersRequest(status=QueryOrderStatus.OPEN)
        )
        self.positions = self.trading_client.get_all_positions()

    def order_buy_market_bracket(self, symbol, notional, limit_price, stop_price):
        print(f"Buying ${notional} of shares of {symbol} at a limit of ${limit_price}")
        req = MarketOrderRequest(
            symbol=symbol,
            notional=notional,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            Class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=limit_price),
            stop_loss=StopLossRequest(stop_price=stop_price),
        )

        res = self.trading_client.submit_order(req)
        return res

    # NOTE: Not working. Shows up as a Market Order
    # def order_buy_limit_bracket(
    #     self, symbol, notional, buy_limit_price, profit_limit_price, stop_price
    # ):
    #     current_price = self.get_stock_current_price(symbol)[symbol].ask_price
    #     qty = int(notional // current_price)
    #     if qty < 1:
    #         print(f"❌ Not enough money to buy {qty} shares of {symbol}")
    #         return False
    #     print(f"Buying {qty} shares of {symbol} at a limit of ${buy_limit_price}")
    #     req = MarketOrderRequest(
    #         symbol=symbol,
    #         qty=qty,
    #         side=OrderSide.BUY,
    #         type=OrderType.LIMIT,
    #         time_in_force=TimeInForce.GTC,
    #         Class=OrderClass.BRACKET,
    #         take_profit=TakeProfitRequest(limit_price=profit_limit_price),
    #         stop_loss=StopLossRequest(stop_price=stop_price),
    #     )
    #
    #     res = self.trading_client.submit_order(req)
    #     return res

    def order_buy_limit_stop_loss(self, symbol, notional, limit_price, stop_price):
        current_price = self.get_stock_current_price(symbol)[symbol].ask_price
        qty = int(notional // current_price)
        if qty < 1:
            print(f"❌ Not enough money to buy {qty} shares of {symbol}")
            return False
        print(f"Buying {qty} shares of {symbol} at a limit of ${limit_price}")
        req = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.GTC,
            Class=OrderClass.OTO,
            stop_loss=StopLossRequest(stop_price=stop_price),
        )

        res = self.trading_client.submit_order(req)
        return res

    def order_trailing_stop(self, symbol, trail_percent=0.2):
        qty = self.get_stock_currently_owned(symbol)
        if qty:
            req = TrailingStopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                trail_price=trail_percent,
                trail_percent=None,
            )

            res = self.trading_client.submit_order(req)
            return res
        else:
            print(f"❌ Not enough shares of {symbol} to sell")
            return False

    def get_stock_current_price(self, symbol):
        req = StockQuotesRequest(symbol_or_symbols=[symbol])
        res = self.historical_client.get_stock_latest_quote(req)
        return res

    def get_stock_currently_owned(self, symbol):
        try:
            position = self.trading_client.get_open_position(symbol)
            return position.qty
        except Exception as e:
            print(f"Error getting position: {e}")
            return 0

    def cancel_all_open_orders(self):
        self.trading_client.cancel_orders()

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
            bars = self.historical_client.get_stock_bars(request_params)

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
