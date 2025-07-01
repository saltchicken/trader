from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import datetime


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
        dates_as_floats = (
            self.data.df.index.astype(np.int64) / 1e9
        )  # nanoseconds to seconds
        self.dates = self.I(lambda: dates_as_floats, name="DateIndex")

    def next(self):
        if len(self.data) < self.volume_period:
            return

        current_ts = self.dates[-1]  # float seconds since epoch
        current_date = datetime.datetime.fromtimestamp(current_ts)

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
