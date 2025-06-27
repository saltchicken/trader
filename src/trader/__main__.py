from finance_client import FinanceClient
from database import DatabaseClient
import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
import matplotlib.pyplot as plt
import ta
import os
import sys


from pprint import pprint

main_dir = os.path.dirname(os.path.abspath(sys.modules["__main__"].__file__))
style_path = os.path.join(main_dir, "dark.mplstyle")
plt.style.use(style_path)

if __name__ == "__main__":
    client = FinanceClient()
    db = DatabaseClient("stock_data")

    def quote_history_test():
        data = client.get_quote_history("T", "10y")
        data["SMA_20"] = ta.trend.sma_indicator(data["Close"], window=20)
        print(data)

    def plot_close_data():
        data = client.get_quote_history("T", "10y")
        plt.plot(data["Close"])
        plt.show()

    def filings_test():
        filings = client.get_filings("PSNL", "2022-01-01", "2025-12-31")

        target_form = "8-K"
        target_filings = [f for f in filings if f["form"] == target_form]
        # print(target_filings)

        df = pd.DataFrame(filings)
        unique_forms = df["form"].unique().tolist()
        print(unique_forms)

    def metrics_test():
        metrics = client.get_metrics("PSNL")
        df = pd.DataFrame(metrics)
        print(df["metric"]["52WeekHigh"])
        # unique_metrics = df["metric"].unique().tolist()
        # print(unique_metrics)
        # print(df.columns.tolist())

    def interesting_metrics(symbol):
        metrics = client.get_metrics(symbol)
        df = pd.DataFrame(metrics)
        result = {}
        result["52WeekHigh"] = df["metric"]["52WeekHigh"]
        result["revenuePerShareAnnual"] = df["metric"]["revenuePerShareAnnual"]
        print(result)

    def ic_report():
        financials = client.get_financials("PSNL")
        df = pd.DataFrame(financials)
        for row in df["data"]:
            print(row["year"])
            pprint(row["report"]["ic"])

    def basic_financials():
        financials = client.client.company_basic_financials("PSNL", "all")
        pprint(financials)

        # symbol_to_check = "CLOV"
        #
        # if symbol_to_check in df_filtered["symbol"].values:
        #     print(f"{symbol_to_check} exists in the list.")
        # else:
        #     print(f"{symbol_to_check} does NOT exist in the list.")

        # print(df_filtered[["symbol", "description", "mic"]].head())
        #
    def update_database_with_rps(symbol):
        if db.does_symbol_and_year_exist(symbol, 2022):
            print(f"{symbol} already exists in database")
            return
        
        rps = client.get_revenue_per_share_history(symbol)
        if not rps:
            print(f"No RPS data for {symbol}")
            return
        for entry in rps:
            db.update_rps(symbol, entry["Year"], entry["Revenue Per Share"])

    for symbol in client.get_all_stocks():
        print(symbol)
        update_database_with_rps(symbol["symbol"])

    # db.print_table()
    # print(db.does_symbol_and_year_exist("FL", 2022))

