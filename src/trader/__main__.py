import matplotlib.pyplot as plt
from pathlib import Path

from .agent import Trader
from .strategies import VolumeBreakoutStrategy, SimpleVolumeStrategy


style_path = Path(__file__).parent / "config" / "dark.mplstyle"
plt.style.use(style_path)


def main():
    trader = Trader()
    symbols = ["AAPL", "MSFT", "GOOGL"]
    trader.backtest_optimize(symbols, SimpleVolumeStrategy)
    # df = trader.get_top()
    # print(df.columns)
    # top_revenue_growth = df.sort_values("roe_ttm", ascending=False).head(20)
    # print(top_revenue_growth[["symbol", "roe_ttm"]])

    # trader.update_symbols()
    # #
    # trader.daily_update()

    # Test symbols - using highly liquid stocks


if __name__ == "__main__":
    main()
