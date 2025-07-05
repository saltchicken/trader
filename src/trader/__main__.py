import matplotlib.pyplot as plt
from pathlib import Path

from .agent import Trader
from .strategies import VolumeBreakoutStrategy, SimpleVolumeStrategy


style_path = Path(__file__).parent / "config" / "dark.mplstyle"
plt.style.use(style_path)


def main():
    trader = Trader()

    # trader.alpaca.cancel_all_open_orders()

    # for order in trader.alpaca.orders:
    #     print(order.symbol, order.qty, order.side, order.status, order.type)

    # trader.alpaca.order_buy_market_bracket("AAPL", 100, 150, 140)

    # symbols = ["AAPL", "MSFT", "GOOGL"]
    # trader.backtest_optimize(symbols, SimpleVolumeStrategy)

    df = trader.get_top()
    top_companies = df["symbol"].head(20).to_list()
    results = trader.get_crosses(top_companies)
    for company in top_companies:
        print(company, trader.interpret_crosses(results[company]))

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
