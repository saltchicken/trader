import yfinance as yf
import pandas as pd
import ta

symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA"]
buy_signals = []
sell_signals = []

for symbol in symbols:
    df = yf.download(symbol, period="6mo", interval="1d")
    df = df.dropna()
    close = pd.Series(df["Close"].values.flatten(), index=df.index, name="Close")
    print(df)
    print(close)


    df["sma_50"] = ta.trend.SMAIndicator(close, window=50).sma_indicator()
    df["sma_200"] = ta.trend.SMAIndicator(close, window=200).sma_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(close).rsi()


    latest = df.iloc[-1]
    # print(latest["rsi"].values)

    # BUY signal
    if latest["rsi"].values[0] < 30 and latest["sma_50"].values[0] > latest["sma_200"].values[0]:
        buy_signals.append(symbol)

    # SELL signal
    if latest["rsi"].values[0] > 70 or latest["Close"].values[0] < latest["sma_200"].values[0]:
        sell_signals.append(symbol)

print("BUY:", buy_signals)
print("SELL:", sell_signals)

