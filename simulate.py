import yfinance as yf
import pandas as pd

pd.set_option("display.max_rows", None)      # Show all rows
pd.set_option("display.max_columns", None)   # Show all columns
pd.set_option("display.width", None)         # Don't wrap lines
pd.set_option("display.max_colwidth", None)  # Show full column contents
import ta
from datetime import datetime, timedelta

symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "PSNL"]
start_date = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")
end_date = datetime.today().strftime("%Y-%m-%d")

# Store results
history = []

for symbol in symbols:
    df = yf.download(symbol, start=start_date, end=end_date, interval="1d", auto_adjust=True)
    df = df.dropna()
    df["Close"] = df["Close"].astype(float)
    
    close = pd.Series(df["Close"].values.flatten(), index=df.index, name="Close")
    df["sma_50"] = ta.trend.SMAIndicator(close, window=50).sma_indicator()
    df["sma_200"] = ta.trend.SMAIndicator(close, window=200).sma_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(close).rsi()

    position = False  # Simulated position tracking
    position_stock_price = 0

    for i in range(200, len(df)):  # Start after 200th day to have valid SMA200
        day = df.iloc[i]
        date = df.index[i].strftime("%Y-%m-%d")

        rsi = day["rsi"].values[0]
        sma_50 = day["sma_50"].values[0]
        sma_200 = day["sma_200"].values[0]
        close_price = day["Close"].values[0]

        if pd.isna(rsi) or pd.isna(sma_50) or pd.isna(sma_200):
            continue

        signal = None

        # BUY signal
        if rsi < 30 and sma_50 > sma_200 and not position:
            signal = "BUY"
            position = True
            position_stock_price = close_price

        # SELL signal
        elif (rsi > 70 or close_price < sma_200) and position and close_price > position_stock_price * 1.10:
            signal = "SELL"
            position = False

        if signal:
            history.append({
                "date": date,
                "symbol": symbol,
                "price": close_price,
                "signal": signal
            })

# Output results
df_signals = pd.DataFrame(history)
print(df_signals)
df_signals.to_csv("trade_signals.csv", index=False)

