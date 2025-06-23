import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

plt.style.use("dark.mplstyle")

symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "SPY"]


def calculate_indicators(df):
    # MACD
    df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # Moving Averages
    df["sma_50"] = df["Close"].rolling(window=50).mean()
    df["sma_200"] = df["Close"].rolling(window=200).mean()

    return df


def find_crosses(df):
    # MACD Crosses
    bullish_macd = (df["macd"].shift(1) < df["signal"].shift(1)) & (
        df["macd"] > df["signal"]
    )
    bearish_macd = (df["macd"].shift(1) > df["signal"].shift(1)) & (
        df["macd"] < df["signal"]
    )

    # Golden/Death Crosses
    golden_cross = (df["sma_50"].shift(1) < df["sma_200"].shift(1)) & (
        df["sma_50"] > df["sma_200"]
    )
    death_cross = (df["sma_50"].shift(1) > df["sma_200"].shift(1)) & (
        df["sma_50"] < df["sma_200"]
    )

    return df[bullish_macd], df[bearish_macd], df[golden_cross], df[death_cross]


for symbol in symbols:
    df = yf.download(symbol, period="5y", interval="1d")
    df = calculate_indicators(df)
    bull_macd, bear_macd, golden, death = find_crosses(df)

    plt.figure(figsize=(14, 6))
    plt.plot(df["Close"], label="Close Price", color="black", linewidth=1.2)

    # MACD crossover markers
    plt.scatter(
        bull_macd.index,
        bull_macd["Close"],
        color="green",
        marker="^",
        label="Bullish MACD",
        zorder=5,
    )
    plt.scatter(
        bear_macd.index,
        bear_macd["Close"],
        color="red",
        marker="v",
        label="Bearish MACD",
        zorder=5,
    )

    # Golden/Death Cross markers with updated marker and color
    plt.scatter(
        golden.index,
        golden["Close"],
        color="yellow",
        marker="P",
        label="Golden Cross",
        zorder=5,
    )
    plt.scatter(
        death.index,
        death["Close"],
        color="blue",
        marker="P",
        label="Death Cross",
        zorder=5,
    )

    plt.title(f"{symbol} - Price with MACD & SMA Crossovers")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
