from finance_client import FinanceClient
from database import DatabaseClient
import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
import matplotlib.pyplot as plt
import ta
import os
import sys


from pprint import pprint

main_dir = os.path.dirname(os.path.abspath(sys.modules["__main__"].__file__))
style_path = os.path.join(main_dir, "dark.mplstyle")
plt.style.use(style_path)


class Trader:
    def __init__(self):
        self.client = FinanceClient()
        self.db = DatabaseClient("stock_data")

    def update_symbols(self):
        symbols = self.client.get_all_stocks()
        new_symbols = []

        for symbol in symbols:
            if not self.db.does_symbol_exist(symbol):
                new_symbols.append(symbol)

        if new_symbols:
            print(f"Adding {len(new_symbols)} new symbols.")
            self.db.update_symbols(new_symbols)
        else:
            print("No new symbols to add.")

    def daily_update(self):
        for symbol in self.db.get_all_symbols():
            print(symbol)
            if self.db.was_updated_today(symbol):
                print(f"{symbol} already updated today. Skipping.")
                continue

            metrics = self.client.get_metrics(symbol)
            self.db.daily_update(symbol, metrics["metric"])


if __name__ == "__main__":
    trader = Trader()
    trader.update_symbols()

    # trader.daily_update()

    # db.add_new_column("stock", "three_month_average_trading_volume", "FLOAT")

    # trader.db.print_table("companies")
    # trader.db.print_table("metric_snapshots")
    # trader.db.print_table("current_metrics")

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
