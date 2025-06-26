import yfinance as yf

# Example: Download S&P 500 ticker list
sp500 = yf.Ticker("^GSPC")
print(sp500.info)  # Does not provide components directly
