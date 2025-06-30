import os
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockLatestTradeRequest, StockBarsRequest, StockSnapshotRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pandas as pd

# Load environment variables from .env file
load_dotenv()

class AlpacaMarketData:
    def __init__(self):
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.secret_key = os.getenv('APCA_API_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file")
        
        # Initialize the historical data client
        self.client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
    
    def get_latest_quote(self, symbol):
        """Get the latest quote for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            response = self.client.get_stock_latest_quote(request)
            return response[symbol]
        except Exception as e:
            print(f"Error getting latest quote: {e}")
            return None
    
    def get_latest_trade(self, symbol):
        """Get the latest trade for a symbol"""
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            response = self.client.get_stock_latest_trade(request)
            return response[symbol]
        except Exception as e:
            print(f"Error getting latest trade: {e}")
            return None
    
    def get_daily_bars(self, symbol, days_back=5):
        """Get recent daily bars (OHLCV) for a symbol"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            response = self.client.get_stock_bars(request)
            return response[symbol]
        except Exception as e:
            print(f"Error getting daily bars: {e}")
            return None
    
    def get_snapshot(self, symbol):
        """Get comprehensive snapshot data"""
        try:
            request = StockSnapshotRequest(symbol_or_symbols=symbol)
            response = self.client.get_stock_snapshot(request)
            return response[symbol]
        except Exception as e:
            print(f"Error getting snapshot: {e}")
            return None
    
    def get_intraday_bars(self, symbol, minutes=60):
        """Get recent intraday bars"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=8)  # Last 8 hours
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=start_date,
                end=end_date,
                limit=minutes
            )
            response = self.client.get_stock_bars(request)
            return response[symbol]
        except Exception as e:
            print(f"Error getting intraday bars: {e}")
            return None

def format_currency(value):
    """Format a number as currency"""
    return f"${value:,.2f}" if value else "N/A"

def format_timestamp(timestamp):
    """Format timestamp for display"""
    if timestamp:
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"

def main():
    try:
        # Initialize the API client
        alpaca = AlpacaMarketData()
        symbol = "AAPL"
        
        print(f"Getting current market data for {symbol}...")
        print("=" * 60)
        
        # Get comprehensive snapshot
        snapshot = alpaca.get_snapshot(symbol)
        
        if snapshot:
            print("📊 MARKET SNAPSHOT:")
            print(f"   Symbol: {symbol}")
            print(f"   Timestamp: {format_timestamp(getattr(snapshot, 'timestamp', None))}")
            print()
            
            # Latest Quote
            if hasattr(snapshot, 'latest_quote') and snapshot.latest_quote:
                quote = snapshot.latest_quote
                print("💰 LATEST QUOTE:")
                print(f"   Bid Price: {format_currency(quote.bid_price)}")
                print(f"   Ask Price: {format_currency(quote.ask_price)}")
                print(f"   Bid Size: {quote.bid_size:,} shares")
                print(f"   Ask Size: {quote.ask_size:,} shares")
                print(f"   Spread: {format_currency(quote.ask_price - quote.bid_price)}")
                print(f"   Quote Time: {format_timestamp(quote.timestamp)}")
                print()
            
            # Latest Trade
            if hasattr(snapshot, 'latest_trade') and snapshot.latest_trade:
                trade = snapshot.latest_trade
                print("🔄 LATEST TRADE:")
                print(f"   Price: {format_currency(trade.price)}")
                print(f"   Size: {trade.size:,} shares")
                print(f"   Trade Time: {format_timestamp(trade.timestamp)}")
                print()
            
            # Daily Bar
            if hasattr(snapshot, 'daily_bar') and snapshot.daily_bar:
                bar = snapshot.daily_bar
                print("📈 TODAY'S STATISTICS:")
                print(f"   Open: {format_currency(bar.open)}")
                print(f"   High: {format_currency(bar.high)}")
                print(f"   Low: {format_currency(bar.low)}")
                print(f"   Close: {format_currency(bar.close)}")
                print(f"   Volume: {bar.volume:,} shares")
                print(f"   VWAP: {format_currency(bar.vwap)}")
                print(f"   Trade Count: {bar.trade_count:,}")
                print()
            
            # Previous Day Bar for comparison
            if hasattr(snapshot, 'previous_daily_bar') and snapshot.previous_daily_bar:
                prev_bar = snapshot.previous_daily_bar
                current_price = snapshot.latest_trade.price if snapshot.latest_trade else None
                
                if current_price and prev_bar.close:
                    change = current_price - prev_bar.close
                    change_pct = (change / prev_bar.close) * 100
                    
                    print("📊 PRICE CHANGE (vs Previous Close):")
                    print(f"   Previous Close: {format_currency(prev_bar.close)}")
                    print(f"   Current Price: {format_currency(current_price)}")
                    print(f"   Change: {change:+.2f} ({change_pct:+.2f}%)")
                    print(f"   Previous Volume: {prev_bar.volume:,} shares")
                    print()
        
        # Get additional data separately if snapshot doesn't have everything
        print("📋 ADDITIONAL DATA:")
        
        # Get recent daily bars for trend analysis
        daily_bars = alpaca.get_daily_bars(symbol, days_back=5)
        if daily_bars and len(daily_bars) > 1:
            print(f"   Last 5 days trading range:")
            for i, bar in enumerate(daily_bars[-5:]):
                date_str = bar.timestamp.strftime("%Y-%m-%d")
                print(f"     {date_str}: {format_currency(bar.low)} - {format_currency(bar.high)} (Vol: {bar.volume:,})")
        
        # Get recent quotes for more detailed analysis
        latest_quote = alpaca.get_latest_quote(symbol)
        if latest_quote:
            mid_price = (latest_quote.bid_price + latest_quote.ask_price) / 2
            spread_pct = ((latest_quote.ask_price - latest_quote.bid_price) / mid_price) * 100
            print(f"   Mid Price: {format_currency(mid_price)}")
            print(f"   Spread %: {spread_pct:.4f}%")
        
        print("\n" + "=" * 60)
        print("Note: Data provided by Alpaca Markets")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. Installed alpaca-py: pip install alpaca-py")
        print("2. Set up your .env file with ALPACA_API_KEY and ALPACA_SECRET_KEY")
        print("3. Valid Alpaca account with market data permissions")

if __name__ == "__main__":
    main()
