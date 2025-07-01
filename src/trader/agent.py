from sqlalchemy import func, desc
from sqlalchemy.orm import aliased
from .finance_client import FinanceClient
from .database import DatabaseClient, Company, MetricSnapshot
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from .strategies import (
    VolumeBreakoutStrategy,
    VolumeReversalStrategy,
    SimpleVolumeStrategy,
)

from datetime import datetime, timedelta

from pprint import pprint

from dotenv import load_dotenv
from .log import logger
import os

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError

load_dotenv()


class Trader:
    def __init__(self):
        self.client = FinanceClient()
        self.db = DatabaseClient("stock_data")

    def update_symbols(self):
        companies = self.client.get_all_stocks()
        new_companies = []

        for company in companies:
            if not self.db.does_symbol_exist(company["symbol"]):
                new_companies.append(company)

        if new_companies:
            logger.debug(f"Adding {len(new_companies)} new symbols.")
            self.db.update_symbols(new_companies)
        else:
            logger.debug("No new symbols to add.")

    def daily_update(self):
        if not self.is_within_allowed_update_window():
            logger.error("Not within allowed update window. Skipping.")
            return

        for symbol in self.db.get_all_symbols():
            logger.debug(symbol)
            if self.db.was_updated_in_nightly_window(symbol):
                logger.warning(
                    f"{symbol} already updated during the current nightly window. Skipping."
                )
                continue

            metrics = self.client.get_metrics(symbol)
            self.db.daily_update(symbol, metrics["metric"])

    def is_within_allowed_update_window(self):
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        if now.hour >= 18 or now.hour < 2:
            return True
        return False

    def get_latest(self, limit=10):
        subquery = (
            self.db.session.query(
                MetricSnapshot.symbol,
                func.max(MetricSnapshot.timestamp).label("latest"),
            )
            .group_by(MetricSnapshot.symbol)
            .subquery()
        )

        alias = aliased(MetricSnapshot)

        query = (
            self.db.session.query(alias.symbol, alias.month3_average_trading_volume)
            .join(
                subquery,
                (alias.symbol == subquery.c.symbol)
                & (alias.timestamp == subquery.c.latest),
            )
            .filter(alias.month3_average_trading_volume != None)
            .order_by(alias.month3_average_trading_volume.desc())
            .limit(limit)
        )

        return query.all()

    def get_snapshots_from_past_day(self):
        now_utc = datetime.now(tz=ZoneInfo("UTC"))
        one_day_ago = now_utc - timedelta(days=2)

        snapshots = (
            self.db.session.query(MetricSnapshot)
            .filter(MetricSnapshot.timestamp >= one_day_ago)
            .order_by(MetricSnapshot.timestamp.desc())
            .all()
        )

        logger.info(f"Found {len(snapshots)} snapshots from the past day.")

        # Convert to DataFrame
        df = pd.DataFrame([s.__dict__ for s in snapshots])
        # df = df.drop(columns=["_sa_instance_state"])  # Drop SQLAlchemy internal column
        return df

    def score_snapshots(self):
        df = self.get_snapshots_from_past_day()

        if df.empty:
            logger.warning("No data to score.")
            return df

        # Normalize and add scoring columns
        def normalize_metric(df, column, higher_is_better=True):
            if df[column].isnull().all():
                return pd.Series([0] * len(df))  # Avoid NaNs if whole column is null

            min_val = df[column].min()
            max_val = df[column].max()
            if max_val == min_val:
                return pd.Series([1] * len(df))  # All values are the same
            if higher_is_better:
                return (df[column] - min_val) / (max_val - min_val)
            else:
                return (max_val - df[column]) / (max_val - min_val)

        # Rename columns to match your expected inputs (if needed)
        df["peTTM"] = df["pe_ttm"]
        df["epsGrowth5Y"] = df["eps_growth_5y"]
        df["roeTTM"] = df["roe_ttm"]
        df["debtToEquity"] = df["long_term_debt_equity_quarterly"]
        df["grossMarginTTM"] = df["gross_margin_ttm"]
        df["revenueGrowth5Y"] = df["revenue_growth_5y"]
        df["pfcfShareTTM"] = df["pfcf_share_ttm"]

        # Apply score calculations
        df["score_pe"] = normalize_metric(df, "peTTM", higher_is_better=False)
        df["score_eps_growth"] = normalize_metric(df, "epsGrowth5Y", True)
        df["score_roe"] = normalize_metric(df, "roeTTM", True)
        df["score_debt"] = normalize_metric(df, "debtToEquity", False)
        df["score_margin"] = normalize_metric(df, "grossMarginTTM", True)
        df["score_revenue_growth"] = normalize_metric(df, "revenueGrowth5Y", True)
        df["score_pfcf"] = normalize_metric(df, "pfcfShareTTM", False)

        return df

    def composite_score(self, df):
        df["composite_score"] = (
            0.15 * df["score_pe"]
            + 0.15 * df["score_eps_growth"]
            + 0.15 * df["score_roe"]
            + 0.1 * df["score_debt"]
            + 0.15 * df["score_margin"]
            + 0.15 * df["score_revenue_growth"]
            + 0.15 * df["score_pfcf"]
        )
        df["rating"] = (df["composite_score"] * 100).round(1)
        df = df.sort_values("rating", ascending=False)
        return df

    def get_top_by_metric(self, metric_name, limit=5):
        """Get top symbols by a specific metric score from latest snapshots"""
        df = self.score_snapshots()

        if df.empty:
            logger.warning(f"No data to get top {metric_name}.")
            return df

        # Keep only the latest snapshot for each symbol
        latest_snapshots = (
            df.sort_values("timestamp").groupby("symbol").last().reset_index()
        )

        # Sort by the specified metric and get top results
        top_results = latest_snapshots.nlargest(limit, metric_name)
        return top_results

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

    def get_stock_data(self, symbol, stock_data_cache=None):
        """Get stock data for a single symbol from cache or return None"""
        if stock_data_cache is None:
            print(f"❌ No cached data available for {symbol}")
            return None

        return stock_data_cache.get(symbol)

    def run_backtest(self, symbol, strategy_class, stock_data_cache=None, **kwargs):
        """Run backtest for a given symbol and strategy"""
        print(f"\n{'=' * 60}")
        print(f"🔍 Running {strategy_class.__name__} for {symbol}")
        print(f"{'=' * 60}")

        # Get data from cache
        data = self.get_stock_data(symbol, stock_data_cache)
        if data is None:
            print(f"❌ Skipping {symbol} due to data issues")
            return None

        try:
            # Run backtest
            bt = Backtest(data, strategy_class, cash=100000, commission=0.002)

            # Run backtest
            if not kwargs:
                print("📊 Running backtest...")
                result = bt.run()
            else:
                print("🔧 Optimizing parameters...")
                result = bt.optimize(**kwargs, maximize="Sharpe Ratio", max_tries=20)

            # Display results
            print(f"\n📈 Backtest Results for {symbol}:")
            print(f"   Total Return:     {result['Return [%]']:.2f}%")
            print(f"   Buy & Hold:       {result['Buy & Hold Return [%]']:.2f}%")
            print(f"   Sharpe Ratio:     {result['Sharpe Ratio']:.2f}")
            print(f"   Max Drawdown:     {result['Max. Drawdown [%]']:.2f}%")
            print(f"   Number of Trades: {result['# Trades']}")

            if result["# Trades"] > 0:
                print(f"   Win Rate:         {result['Win Rate [%]']:.1f}%")
                print(f"   Avg Trade:        {result['Avg. Trade [%]']:.2f}%")

            return result

        except Exception as e:
            print(f"❌ Error running backtest for {symbol}: {e}")
            print(f"   Error type: {type(e).__name__}")
            return None
