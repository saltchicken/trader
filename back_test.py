import yfinance as yf
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import warnings

warnings.filterwarnings("ignore")


class VolumeBreakoutStrategy(Strategy):
    """
    Volume-based breakout strategy that combines:
    1. Volume spike detection (volume > average volume * threshold)
    2. Price momentum confirmation
    3. Simple trend following with volume confirmation
    """

    # Strategy parameters
    volume_threshold = 2.0  # Volume must be 2x average volume
    volume_period = 20  # Period for volume moving average
    price_period = 10  # Period for price moving average
    stop_loss_pct = 0.05  # 5% stop loss
    take_profit_pct = 0.15  # 15% take profit

    def init(self):
        # Calculate volume indicators using backtesting.py's I() method properly
        def volume_sma(arr, n):
            return pd.Series(arr).rolling(n, min_periods=1).mean()

        def price_sma(arr, n):
            return pd.Series(arr).rolling(n, min_periods=1).mean()

        self.volume_ma = self.I(
            volume_sma, self.data.Volume, self.volume_period, name="Volume_MA"
        )
        self.price_ma = self.I(
            price_sma, self.data.Close, self.price_period, name="Price_MA"
        )

        # Track entry price manually
        self.entry_price = None

    def next(self):
        # Get current values safely
        current_volume = self.data.Volume[-1]
        current_price = self.data.Close[-1]

        # Ensure we have valid data
        if len(self.data) < max(self.volume_period, self.price_period):
            return

        try:
            avg_volume = self.volume_ma[-1]
            price_ma_val = self.price_ma[-1]
        except (IndexError, TypeError):
            return

        if pd.isna(avg_volume) or pd.isna(price_ma_val) or avg_volume == 0:
            return

        # Entry conditions
        volume_spike = current_volume > (avg_volume * self.volume_threshold)
        price_above_ma = current_price > price_ma_val

        # Additional momentum check
        price_momentum = True
        if len(self.data.Close) > 1:
            price_momentum = current_price > self.data.Close[-2]

        # Entry signal: Volume spike + Price momentum
        if not self.position and volume_spike and price_above_ma and price_momentum:
            self.buy()
            self.entry_price = current_price

        # Exit conditions
        elif self.position and self.entry_price is not None:
            # Take profit
            if current_price >= self.entry_price * (1 + self.take_profit_pct):
                self.position.close()
                self.entry_price = None

            # Stop loss
            elif current_price <= self.entry_price * (1 - self.stop_loss_pct):
                self.position.close()
                self.entry_price = None


class VolumeReversalStrategy(Strategy):
    """
    Volume-based mean reversion strategy
    """

    volume_threshold = 3.0  # Volume must be 3x average
    volume_period = 20
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    bb_period = 20
    bb_std = 2

    def init(self):
        # Volume indicators
        def volume_sma(arr, n):
            return pd.Series(arr).rolling(n, min_periods=1).mean()

        self.volume_ma = self.I(
            volume_sma, self.data.Volume, self.volume_period, name="Volume_MA"
        )

        # RSI calculation
        def rsi_calc(prices, period):
            prices_series = pd.Series(prices)
            delta = prices_series.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=period, min_periods=1).mean()
            avg_loss = loss.rolling(window=period, min_periods=1).mean()

            # Avoid division by zero
            avg_loss = avg_loss.replace(0, 0.0001)
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        self.rsi = self.I(rsi_calc, self.data.Close, self.rsi_period, name="RSI")

        # Bollinger Bands
        def bb_calc(prices, period, std_dev):
            prices_series = pd.Series(prices)
            sma = prices_series.rolling(window=period, min_periods=1).mean()
            std = prices_series.rolling(window=period, min_periods=1).std()

            upper = sma + (std * std_dev)
            middle = sma
            lower = sma - (std * std_dev)

            return upper, middle, lower

        bb_result = self.I(
            bb_calc, self.data.Close, self.bb_period, self.bb_std, name="BB"
        )
        self.bb_upper = bb_result[0]
        self.bb_middle = bb_result[1]
        self.bb_lower = bb_result[2]

        self.entry_price = None

    def next(self):
        current_volume = self.data.Volume[-1]
        current_price = self.data.Close[-1]

        # Ensure we have enough data
        if len(self.data) < max(self.volume_period, self.rsi_period, self.bb_period):
            return

        try:
            avg_volume = self.volume_ma[-1]
            current_rsi = self.rsi[-1]
            bb_lower_val = self.bb_lower[-1]
            bb_middle_val = self.bb_middle[-1]
        except (IndexError, TypeError):
            return

        if any(pd.isna([avg_volume, current_rsi, bb_lower_val, bb_middle_val])):
            return

        volume_spike = current_volume > (avg_volume * self.volume_threshold)

        # Long entry: Oversold + Volume spike + Below lower BB
        if (
            not self.position
            and volume_spike
            and current_rsi < self.rsi_oversold
            and current_price < bb_lower_val
        ):
            self.buy()
            self.entry_price = current_price

        # Exit conditions for long positions
        elif self.position and self.entry_price is not None:
            if current_price > bb_middle_val:
                self.position.close()
                self.entry_price = None


class SimpleVolumeStrategy(Strategy):
    """
    Simplified volume strategy for demonstration
    """

    volume_threshold = 2.0
    volume_period = 20
    hold_days = 5

    def init(self):
        # Simple volume moving average
        def volume_sma(arr, n):
            return pd.Series(arr).rolling(n, min_periods=1).mean()

        self.volume_ma = self.I(
            volume_sma, self.data.Volume, self.volume_period, name="Volume_MA"
        )
        self.entry_bar = None

    def next(self):
        if len(self.data) < self.volume_period:
            return

        try:
            avg_volume = self.volume_ma[-1]
        except (IndexError, TypeError):
            return

        if pd.isna(avg_volume) or avg_volume == 0:
            return

        current_volume = self.data.Volume[-1]
        current_price = self.data.Close[-1]
        current_open = self.data.Open[-1]

        # Entry: Volume spike + Green candle
        if (
            not self.position
            and current_volume > avg_volume * self.volume_threshold
            and current_price > current_open
        ):  # Green candle
            self.buy()
            self.entry_bar = len(self.data) - 1

        # Exit: After hold_days or 10% profit
        elif self.position and self.entry_bar is not None:
            bars_held = len(self.data) - 1 - self.entry_bar
            entry_price = self.data.Close[self.entry_bar]
            profit_pct = (current_price - entry_price) / entry_price

            if bars_held >= self.hold_days or profit_pct >= 0.10:
                self.position.close()
                self.entry_bar = None


def get_stock_data(symbol, period="2y"):
    """Download stock data using yfinance"""
    try:
        print(f"📥 Downloading data for {symbol}...")
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)

        if data.empty:
            raise ValueError(f"No data found for symbol {symbol}")

        # Ensure we have the required columns
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Remove any rows with NaN values or zero volume
        data = data.dropna()
        data = data[data["Volume"] > 0]

        if len(data) < 50:  # Need minimum data for analysis
            raise ValueError(f"Insufficient data: only {len(data)} rows")

        print(f"✅ Downloaded {len(data)} rows of data for {symbol}")
        return data

    except Exception as e:
        print(f"❌ Error downloading data for {symbol}: {e}")
        return None


def run_backtest(symbol, strategy_class, **kwargs):
    """Run backtest for a given symbol and strategy"""
    print(f"\n{'=' * 60}")
    print(f"🔍 Running {strategy_class.__name__} for {symbol}")
    print(f"{'=' * 60}")

    # Get data
    data = get_stock_data(symbol)
    if data is None:
        print(f"❌ Skipping {symbol} due to data issues")
        return None

    try:
        # Run backtest
        bt = Backtest(data, strategy_class, cash=100000, commission=0.002)

        # Run backtest
        if not kwargs:
            print("📊 Running backtest...")
            result = bt.run()
        else:
            print("🔧 Optimizing parameters...")
            result = bt.optimize(**kwargs, maximize="Sharpe Ratio", max_tries=20)

        # Display results
        print(f"\n📈 Backtest Results for {symbol}:")
        print(f"   Total Return:     {result['Return [%]']:.2f}%")
        print(f"   Buy & Hold:       {result['Buy & Hold Return [%]']:.2f}%")
        print(f"   Sharpe Ratio:     {result['Sharpe Ratio']:.2f}")
        print(f"   Max Drawdown:     {result['Max. Drawdown [%]']:.2f}%")
        print(f"   Number of Trades: {result['# Trades']}")

        if result["# Trades"] > 0:
            print(f"   Win Rate:         {result['Win Rate [%]']:.1f}%")
            print(f"   Avg Trade:        {result['Avg. Trade [%]']:.2f}%")

        return result

    except Exception as e:
        print(f"❌ Error running backtest for {symbol}: {e}")
        print(f"   Error type: {type(e).__name__}")
        return None


def main():
    """Main function to run volume-based backtesting strategies"""

    print("🚀 VOLUME-BASED TRADING STRATEGY BACKTESTING")
    print("📊 Using yfinance for data and backtesting.py for analysis")
    print("=" * 70)

    # Test symbols - using highly liquid stocks
    symbols = ["AAPL", "MSFT", "GOOGL"]
    strategies = [
        ("Simple Volume", SimpleVolumeStrategy),
        ("Volume Breakout", VolumeBreakoutStrategy),
        ("Volume Reversal", VolumeReversalStrategy),
    ]

    all_results = {}

    # Test each strategy on each symbol
    for symbol in symbols:
        print(f"\n🎯 ANALYZING {symbol}")
        print("-" * 40)

        symbol_results = {}

        for strategy_name, strategy_class in strategies:
            print(f"\n📋 Testing {strategy_name} Strategy")
            result = run_backtest(symbol, strategy_class)

            if result is not None:
                symbol_results[strategy_name] = result
                all_results[f"{symbol}_{strategy_name}"] = result

        # Compare strategies for this symbol
        if symbol_results:
            print(f"\n🏆 BEST STRATEGY FOR {symbol}:")
            best_strategy = max(
                symbol_results.items(), key=lambda x: x[1]["Return [%]"]
            )
            print(
                f"   {best_strategy[0]}: {best_strategy[1]['Return [%]']:.2f}% return"
            )

    # Overall summary
    if all_results:
        print(f"\n{'=' * 70}")
        print("🏅 OVERALL PERFORMANCE SUMMARY")
        print(f"{'=' * 70}")

        # Sort by return
        sorted_results = sorted(
            all_results.items(), key=lambda x: x[1]["Return [%]"], reverse=True
        )

        print(
            f"{'Strategy':<25} {'Return':<10} {'Sharpe':<8} {'Trades':<8} {'Win Rate':<10}"
        )
        print("-" * 70)

        for name, result in sorted_results:
            win_rate = result.get("Win Rate [%]", 0) if result["# Trades"] > 0 else 0
            print(
                f"{name:<25} {result['Return [%]']:>8.2f}% {result['Sharpe Ratio']:>6.2f} "
                f"{result['# Trades']:>6d} {win_rate:>8.1f}%"
            )

    # Parameter optimization example
    print(f"\n🔧 PARAMETER OPTIMIZATION EXAMPLE")
    print("-" * 50)

    try:
        opt_result = run_backtest(
            "AAPL",
            SimpleVolumeStrategy,
            volume_threshold=[1.5, 1.6, 1.4, 2.0, 2.5, 3.0],
            volume_period=[14, 15, 16, 17, 18, 19, 20, 25],
            hold_days=[3, 5, 7, 10],
        )

        if opt_result is not None:
            print(f"\n🎯 Optimized Parameters for AAPL:")
            strategy = opt_result._strategy
            print(f"   Volume Threshold: {strategy.volume_threshold}")
            print(f"   Volume Period:    {strategy.volume_period}")
            print(f"   Hold Days:        {strategy.hold_days}")
            print(f"   Optimized Return: {opt_result['Return [%]']:.2f}%")

    except Exception as e:
        print(f"❌ Optimization failed: {e}")

    print(f"\n✅ Analysis complete!")


if __name__ == "__main__":
    # Check for required packages
    required_packages = ["yfinance", "backtesting", "pandas", "numpy"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print(f"📦 Install with: pip install {' '.join(missing_packages)}")
        exit(1)

    main()
