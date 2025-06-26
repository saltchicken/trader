from finance_client import FinanceClient
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

    def quote_history_test():
        data = client.get_quote_history("T", "10y")
        data["SMA_20"] = ta.trend.sma_indicator(data["Close"], window=20)
        print(data)

    def plot_close_data():
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

    def calc_time_series():
        income_data = client.client.financials_reported(
            symbol="AAPL", statement_type="ic", freq="annual"
        )
        # Get balance sheet (Shares Outstanding)
        balance_data = client.client.financials_reported(
            symbol="AAPL", statement_type="bs", freq="annual"
        )

        for ic, bs in zip(income_data["financials"], balance_data["financials"]):
            year = ic["year"]
            revenue = float(ic.get("Revenue", 0))
            shares = float(bs.get("WeightedAverageShsOut", 0)) or float(
                bs.get("CommonSharesOutstanding", 0)
            )
            if shares:
                rps = revenue / shares
                print(f"{year}: Revenue Per Share = {rps:.2f}")
