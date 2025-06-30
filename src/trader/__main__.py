from .finance_client import FinanceClient
from .database import DatabaseClient, Company
from .agent import Trader
import numpy as np
import pandas as pd

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

main_dir = os.path.dirname(os.path.abspath(sys.modules["__main__"].__file__))
style_path = os.path.join(main_dir, "dark.mplstyle")
plt.style.use(style_path)


if __name__ == "__main__":
    trader = Trader()
    # trader.update_symbols()
    # #
    # trader.daily_update()
    latest = trader.get_latest()
    print(latest)

    # db.add_new_column("stock", "three_month_average_trading_volume", "FLOAT")

    # trader.db.print_table("companies")
    # trader.db.print_table("metric_snapshots")
    # trader.db.print_table("current_metrics")
    company = trader.db.session.query(Company).filter_by(symbol="AAPL").first()

    # if company:
    #     snapshots = company.snapshots
    #     for snapshot in snapshots:
    #         print(snapshot.timestamp, snapshot.week52_high)

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
