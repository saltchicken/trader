from finance_client import FinanceClient
import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
import matplotlib.pyplot as plt
import ta
import os
import sys

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///stock_data.db")

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

    def revenue_per_share(symbol):
        rps = client.get_revenue_per_share_history(symbol)
        return rps

    def stock_symbols():
        symbols = client.client.stock_symbols("US")
        # print(len(symbols))
        # print([s["symbol"] for s in symbols[:10]])  # Print first 10
        df = pd.DataFrame(symbols)
        valid_mics = ["XNYS", "XNAS"]  # NYSE and NASDAQ

        df_filtered = df[(df["type"] == "Common Stock") & (df["mic"].isin(valid_mics))]

        # df_filtered = df_filtered[~df_filtered["symbol"].str.contains(r"\.")]

        # print(f"Filtered count: {len(df_filtered)}")
        # print(df_filtered.to_dict())
        stock_symbol_dict = df_filtered[["symbol", "description"]].to_dict(orient="records")
        return stock_symbol_dict

        # symbol_to_check = "CLOV"
        #
        # if symbol_to_check in df_filtered["symbol"].values:
        #     print(f"{symbol_to_check} exists in the list.")
        # else:
        #     print(f"{symbol_to_check} does NOT exist in the list.")

        # print(df_filtered[["symbol", "description", "mic"]].head())
        #
    def update_database(symbol):
        rps = revenue_per_share(symbol)
        if not rps:
            print(f"No RPS data for {symbol}")
            return
        for entry in rps:
            row = pd.DataFrame([{
                "symbol": symbol,
                "year": entry["Year"],
                "revenue_per_share": entry["Revenue Per Share"]
            }])

            try:
                row.to_sql("test2", con=engine, if_exists="append", index=False)
            except Exception as e:
                print("Already exists", e)

    def test_table():
        df = pd.read_sql_table("test2", con=engine)
        print(df)

    def create_index():
        with engine.connect() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_symbol_date ON test2(symbol, year)"))
        conn.commit()




    # create_index()
    # try:
    #     update_database("GOOG")
    # except Exception as e:
    #     print(e)
    # test_table()

    # revenue_per_share("AAPL")
    stock_symbol_dict = stock_symbols()
    for symbol in stock_symbol_dict:
        print(symbol)
        update_database(symbol["symbol"])
    # test_table()

