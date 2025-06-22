# trading_signals.py

import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt

plt.style.use("dark.mplstyle")


def fetch_data(ticker, start, end):
    data = yf.download(ticker, start=start, end=end)
    data.dropna(inplace=True)
    return data


def add_indicators(data):
    # Force close to be a 1D Series with correct index
    close = pd.Series(data["Close"].values.flatten(), index=data.index, name="Close")

    data["sma_50"] = ta.trend.SMAIndicator(close, window=50).sma_indicator()
    data["sma_200"] = ta.trend.SMAIndicator(close, window=200).sma_indicator()
    data["rsi"] = ta.momentum.RSIIndicator(close).rsi()

    macd = ta.trend.MACD(close)
    data["macd"] = macd.macd_diff()

    return data


def generate_signals(data):
    buy_signals = []
    sell_signals = []
    position = False

    for i in range(len(data)):
        if (
            data["rsi"].iloc[i] < 30
            and data["sma_50"].iloc[i] > data["sma_200"].iloc[i]
            and not position
        ):
            buy_signals.append(data["Close"].iloc[i])
            sell_signals.append(None)
            position = True
        elif data["rsi"].iloc[i] > 70 and position:
            buy_signals.append(None)
            sell_signals.append(data["Close"].iloc[i])
            position = False
        else:
            buy_signals.append(None)
            sell_signals.append(None)

    data["Buy"] = buy_signals
    data["Sell"] = sell_signals
    return data


def plot_signals(data, ticker):
    plt.figure(figsize=(14, 7))
    plt.plot(data["Close"], label="Close Price", alpha=0.5)
    plt.plot(data["sma_50"], label="SMA 50")
    plt.plot(data["sma_200"], label="SMA 200")
    plt.scatter(data.index, data["Buy"], label="Buy Signal", marker="^", color="green")
    plt.scatter(data.index, data["Sell"], label="Sell Signal", marker="v", color="red")
    plt.title(f"{ticker} Trading Signals")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()


def main():
    ticker = "PSNL"
    start = "2022-01-01"
    end = "2025-06-08"

    print(f"Fetching data for {ticker}...")
    data = fetch_data(ticker, start, end)

    print("Calculating indicators...")
    data = add_indicators(data)

    print("Generating signals...")
    data = generate_signals(data)

    print("Plotting signals...")
    plot_signals(data, ticker)


if __name__ == "__main__":
    main()
