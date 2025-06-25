from finance_client import FinanceClient
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('src/trader/dark.mplstyle')

if __name__ == "__main__":
    client = FinanceClient()
    # client.print_filings("AAPL", "2022-01-01", "2022-12-31")
    data = client.get_quote_history("AAPL")
    plt.plot(data["Close"])
    plt.show()

