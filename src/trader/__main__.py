import matplotlib.pyplot as plt
from pathlib import Path

import time
from .agent import Trader
from .strategies import VolumeBreakoutStrategy, SimpleVolumeStrategy


style_path = Path(__file__).parent / "config" / "dark.mplstyle"
plt.style.use(style_path)


def has_stock_gained_10_percent(symbol, start_date, end_date):
    pass


def main():
    trader = Trader()
    trader.db.financials_update()
    # trader.db.fix_symbols()
    # res = trader.alpaca.order_buy_market_bracket("ERO", 1000)
    # res = trader.alpaca.order_request("ARAY", 1000, 1.40)
    # res = trader.alpaca.order_buy_limit_bracket("PAL", 1000, 7.5)
    # print(res)
    # trader.alpaca.test()

    # cik
    # financials

    # symbols = trader.db.get_all_symbols()
    # chunk_size = 100
    # for i in range(0, len(symbols), chunk_size):
    #     print("Chunky")
    #     chunk = symbols[i : i + chunk_size]
    #     print(chunk)
    #     trader.calculate_and_update_scores(chunk)
    #     time.sleep(1.0)

    # symbols = ["AAPL", "MSFT", "GOOGL"]
    # trader.backtest_optimize(symbols, SimpleVolumeStrategy)

    # df = trader.get_top()
    # top_companies = df["symbol"].head(50).to_list()
    # results = trader.get_crosses(top_companies)
    # for company in top_companies:
    #     if trader.interpret_crosses(results[company]) == "buy":
    #         print(f"Buy {company}")
    #         exchange_info = trader.alpaca.get_stock_current_price(company)
    #         current_ask_price = exchange_info[company].ask_price
    #         if exchange_info[company].ask_exchange == ' ': #TODO: Fix magically checking for ' '
    #             print(f"❌ No ask price for {company}")
    #             if current_ask_price == 0.0:
    #                 print(f"❌ Ask price is 0 for {company}")
    #             continue
    #         take_profit = 1.1 * current_ask_price
    #         stop_loss = 0.9 * current_ask_price
    #         print(f"Take profit: {take_profit}, Stop loss: {stop_loss}")
    #         #TODO: Remove magic number of 1000. Calculate notional based on account balance
    #         trader.alpaca.order_buy_market_bracket(company, 1000, take_profit, stop_loss)

    # result = df.sort_values("composite_score", ascending=True).head(50)
    # print(
    #     result[
    #         [
    #             "symbol",
    #             "composite_score",
    #             "roe_ttm",
    #             "pe_ttm",
    #             "long_term_debt_equity_quarterly",
    #             "revenue_growth_5y",
    #             "beta",
    #         ]
    #     ]
    # )
    # print(df.columns)
    # top_revenue_growth = df.sort_values("roe_ttm", ascending=False).head(50)
    # top_revenue_growth["test"] = top_revenue_growth["roe_ttm"] * 100
    # print(top_revenue_growth[["symbol", "roe_ttm", "composite_score"]])


if __name__ == "__main__":
    main()
