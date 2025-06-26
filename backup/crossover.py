import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA"]


def calculate_macd(df):
    df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    return df


def find_macd_crosses(df):
    bullish = (df["macd"].shift(1) < df["signal"].shift(1)) & (
        df["macd"] > df["signal"]
    )
    bearish = (df["macd"].shift(1) > df["signal"].shift(1)) & (
        df["macd"] < df["signal"]
    )
    return df[bullish], df[bearish]


for symbol in symbols:
    df = yf.download(symbol, period="5y", interval="1d")
    df = calculate_macd(df)
    bullish_crosses, bearish_crosses = find_macd_crosses(df)

    plt.figure(figsize=(14, 6))
    plt.plot(df["Close"], label="Close Price", color="black")

    # Plot crossover markers on the price line
    plt.scatter(
        bullish_crosses.index,
        bullish_crosses["Close"],
        color="green",
        marker="^",
        label="Bullish MACD",
        zorder=5,
    )
    plt.scatter(
        bearish_crosses.index,
        bearish_crosses["Close"],
        color="red",
        marker="v",
        label="Bearish MACD",
        zorder=5,
    )

    plt.title(f"{symbol} - Price with MACD Crossovers")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
