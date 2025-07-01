from .finance_client import FinanceClient
from .database import DatabaseClient, Company
from .agent import Trader
import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from .strategies import (
    VolumeBreakoutStrategy,
    VolumeReversalStrategy,
    SimpleVolumeStrategy,
)

from pathlib import Path

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
import matplotlib.pyplot as plt
import ta
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pprint import pprint

style_path = Path(__file__).parent / "config" / "dark.mplstyle"
plt.style.use(style_path)


def main():
    trader = Trader()
    # trader.update_symbols()
    # #
    # trader.daily_update()
    # latest = trader.get_snapshots_from_past_day()
    # print(latest)

    scores = trader.score_snapshots()
    composite_scores = trader.composite_score(scores)
    # print(composite_scores)
    top_scores = composite_scores.nlargest(5, "composite_score")
    for idx, row in top_scores.iterrows():
        print(f"{row['symbol']}: {row['composite_score']:.2f}")
    # print(scores)
    #
    # db.add_new_column("stock", "three_month_average_trading_volume", "FLOAT")

    # trader.db.print_table("companies")
    # trader.db.print_table("metric_snapshots")
    # trader.db.print_table("current_metrics")
    company = trader.db.session.query(Company).filter_by(symbol="AAPL").first()

    # if company:
    #     snapshots = company.snapshots
    #     for snapshot in snapshots:
    #         print(snapshot.timestamp, snapshot.week52_high)
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #

    # """Main function to run volume-based backtesting strategies"""
    #
    # print("🚀 VOLUME-BASED TRADING STRATEGY BACKTESTING")
    # print("📊 Using Alpaca API for data and backtesting.py for analysis")
    # print("=" * 70)
    #
    # # Check environment variables
    # if not os.getenv("APCA_API_KEY_ID") or not os.getenv("APCA_API_SECRET_KEY"):
    #     print("❌ Missing Alpaca API credentials in environment variables")
    #     print(
    #         "   Please ensure APCA_API_KEY_ID and APCA_API_SECRET_KEY are set in your .env file"
    #     )
    #     return
    #
    # # Test symbols - using highly liquid stocks
    # symbols = ["AAPL", "MSFT", "GOOGL", "PSNL"]
    # strategies = [
    #     ("Simple Volume", SimpleVolumeStrategy),
    #     ("Volume Breakout", VolumeBreakoutStrategy),
    #     ("Volume Reversal", VolumeReversalStrategy),
    # ]
    #
    # # Fetch all stock data in a single API call
    # print(f"\n🔄 Fetching data for all symbols...")
    # stock_data_cache = trader.get_all_stock_data(symbols)
    #
    # if stock_data_cache is None:
    #     print("❌ Failed to fetch stock data. Exiting.")
    #     return
    #
    # # Count successful downloads
    # successful_symbols = [s for s in symbols if stock_data_cache.get(s) is not None]
    # print(
    #     f"✅ Successfully loaded data for {len(successful_symbols)} out of {len(symbols)} symbols"
    # )
    #
    # all_results = {}
    #
    # # Test each strategy on each symbol
    # for symbol in symbols:
    #     if stock_data_cache.get(symbol) is None:
    #         print(f"\n⏭️ Skipping {symbol} - no data available")
    #         continue
    #
    #     print(f"\n🎯 ANALYZING {symbol}")
    #     print("-" * 40)
    #
    #     symbol_results = {}
    #
    #     for strategy_name, strategy_class in strategies:
    #         print(f"\n📋 Testing {strategy_name} Strategy")
    #         result = trader.run_backtest(symbol, strategy_class, stock_data_cache)
    #
    #         if result is not None:
    #             symbol_results[strategy_name] = result
    #             all_results[f"{symbol}_{strategy_name}"] = result
    #
    #     # Compare strategies for this symbol
    #     if symbol_results:
    #         print(f"\n🏆 BEST STRATEGY FOR {symbol}:")
    #         best_strategy = max(
    #             symbol_results.items(), key=lambda x: x[1]["Return [%]"]
    #         )
    #         print(
    #             f"   {best_strategy[0]}: {best_strategy[1]['Return [%]']:.2f}% return"
    #         )
    #
    # # Overall summary
    # if all_results:
    #     print(f"\n{'=' * 70}")
    #     print("🏅 OVERALL PERFORMANCE SUMMARY")
    #     print(f"{'=' * 70}")
    #
    #     # Sort by return
    #     sorted_results = sorted(
    #         all_results.items(), key=lambda x: x[1]["Return [%]"], reverse=True
    #     )
    #
    #     print(
    #         f"{'Strategy':<25} {'Return':<10} {'Sharpe':<8} {'Trades':<8} {'Win Rate':<10}"
    #     )
    #     print("-" * 70)
    #
    #     for name, result in sorted_results:
    #         win_rate = result.get("Win Rate [%]", 0) if result["# Trades"] > 0 else 0
    #         print(
    #             f"{name:<25} {result['Return [%]']:>8.2f}% {result['Sharpe Ratio']:>6.2f} "
    #             f"{result['# Trades']:>6d} {win_rate:>8.1f}%"
    #         )
    #
    # # Parameter optimization example
    # print(f"\n🔧 PARAMETER OPTIMIZATION EXAMPLE")
    # print("-" * 50)
    #
    # # Only run optimization if we have AAPL data
    # if stock_data_cache.get("AAPL") is not None:
    #     try:
    #         opt_result = trader.run_backtest(
    #             "AAPL",
    #             SimpleVolumeStrategy,
    #             stock_data_cache,
    #             volume_threshold=[1.5, 1.6, 1.4, 2.0, 2.5, 3.0],
    #             volume_period=[14, 15, 16, 17, 18, 19, 20, 25],
    #             hold_days=[3, 5, 7, 10],
    #         )
    #
    #         if opt_result is not None:
    #             print(f"\n🎯 Optimized Parameters for AAPL:")
    #             strategy = opt_result._strategy
    #             print(f"   Volume Threshold: {strategy.volume_threshold}")
    #             print(f"   Volume Period:    {strategy.volume_period}")
    #             print(f"   Hold Days:        {strategy.hold_days}")
    #             print(f"   Optimized Return: {opt_result['Return [%]']:.2f}%")
    #
    #     except Exception as e:
    #         print(f"❌ Optimization failed: {e}")
    # else:
    #     print("⏭️ Skipping optimization - AAPL data not available")
    #
    # print(f"\n✅ Analysis complete!")
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #

    def quote_history_test():
        data = trader.client.get_quote_history("T", "10y")
        data["SMA_20"] = ta.trend.sma_indicator(data["Close"], window=20)
        print(data)

    def plot_close_data():
        data = trader.client.get_quote_history("T", "10y")
        plt.plot(data["Close"])
        plt.show()

    def filings_test():
        filings = trader.client.get_filings("PSNL", "2022-01-01", "2025-12-31")

        target_form = "8-K"
        target_filings = [f for f in filings if f["form"] == target_form]
        # print(target_filings)

        df = pd.DataFrame(filings)
        unique_forms = df["form"].unique().tolist()
        print(unique_forms)

    def ic_report():
        financials = trader.client.get_financials("PSNL")
        df = pd.DataFrame(financials)
        for row in df["data"]:
            print(row["year"])
            pprint(row["report"]["ic"])

    def basic_financials():
        financials = trader.client.client.company_basic_financials("PSNL", "all")
        pprint(financials)


if __name__ == "__main__":
    main()
