import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA"]


def find_crosses(df):
    # Identify where sma_50 crosses sma_200
    golden_crosses = (df["sma_50"].shift(1) < df["sma_200"].shift(1)) & (
        df["sma_50"] > df["sma_200"]
    )
    death_crosses = (df["sma_50"].shift(1) > df["sma_200"].shift(1)) & (
        df["sma_50"] < df["sma_200"]
    )
    return df[golden_crosses], df[death_crosses]


for symbol in symbols:
    df = yf.download(symbol, period="10y", interval="1d")
    df["sma_50"] = df["Close"].rolling(window=50).mean()
    df["sma_200"] = df["Close"].rolling(window=200).mean()

    golden_crosses, death_crosses = find_crosses(df)

    plt.figure(figsize=(12, 6))
    plt.plot(df["Close"], label="Close", alpha=0.5)
    plt.plot(df["sma_50"], label="SMA 50", color="blue")
    plt.plot(df["sma_200"], label="SMA 200", color="orange")

    plt.scatter(
        golden_crosses.index,
        golden_crosses["Close"],
        color="green",
        marker="^",
        label="Golden Cross",
        zorder=5,
    )
    plt.scatter(
        death_crosses.index,
        death_crosses["Close"],
        color="red",
        marker="v",
        label="Death Cross",
        zorder=5,
    )

    plt.title(f"{symbol} - Golden/Death Crosses")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
