import yfinance as yf

ticker = yf.Ticker("GOOG")

# Quarterly income statement (includes Net Income)
income_quarterly = ticker.quarterly_financials.T

# Quarterly balance sheet (includes shares outstanding)
balance_quarterly = ticker.quarterly_balance_sheet.T

# Combine and rename
df = income_quarterly[['Net Income']].join(
    balance_quarterly[['Ordinary Shares Number']]
).rename(columns={'Net Income': 'Earnings', 'Ordinary Shares Number': 'Shares Outstanding'})

print(df)

