import yfinance as yf
import ta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_apple_data(period="1y"):
    """Download Apple stock data"""
    ticker = yf.Ticker("AAPL")
    data = ticker.history(period=period)
    return data

def calculate_trend_signals(data):
    """Calculate various trend following indicators"""
    df = data.copy()
    
    # Moving Averages
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
    df['EMA_26'] = ta.trend.ema_indicator(df['Close'], window=26)
    
    # MACD
    df['MACD'] = ta.trend.macd(df['Close'])
    df['MACD_signal'] = ta.trend.macd_signal(df['Close'])
    df['MACD_histogram'] = ta.trend.macd_diff(df['Close'])
    
    # ADX (Average Directional Index) - Trend strength
    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'])
    
    # RSI (Relative Strength Index) - Momentum indicator
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # Stochastic Oscillator - Momentum indicator
    df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'])
    df['Stoch_D'] = ta.momentum.stoch_signal(df['High'], df['Low'], df['Close'])
    
    # Williams %R - Momentum indicator
    df['Williams_R'] = ta.momentum.williams_r(df['High'], df['Low'], df['Close'])
    
    # Volume indicators
    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    df['Volume_SMA'] = ta.trend.sma_indicator(df['Volume'], window=20)
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['Close'])
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_middle'] = bb.bollinger_mavg()
    
    # Ichimoku Cloud
    df['Tenkan_sen'] = ta.trend.ichimoku_conversion_line(df['High'], df['Low'])  # Conversion Line (9)
    df['Kijun_sen'] = ta.trend.ichimoku_base_line(df['High'], df['Low'])  # Base Line (26)
    df['Senkou_span_a'] = ta.trend.ichimoku_a(df['High'], df['Low'])  # Leading Span A
    df['Senkou_span_b'] = ta.trend.ichimoku_b(df['High'], df['Low'])  # Leading Span B
    df['Chikou_span'] = df['Close'].shift(-26)  # Lagging Span
    
    # Parabolic SAR
    df['SAR'] = ta.trend.psar_down(df['High'], df['Low'], df['Close'])
    df['SAR_up'] = ta.trend.psar_up(df['High'], df['Low'], df['Close'])
    df['SAR_down'] = ta.trend.psar_down(df['High'], df['Low'], df['Close'])
    df['SAR_bull'] = df['Close'] > df['SAR']  # Bullish when price above SAR
    
    # Generate signals
    df['MA_signal'] = np.where(df['SMA_20'] > df['SMA_50'], 1, -1)  # 1 for bullish, -1 for bearish
    df['MACD_signal_trend'] = np.where(df['MACD'] > df['MACD_signal'], 1, -1)
    df['BB_signal'] = np.where(df['Close'] > df['BB_upper'], -1,  # Sell when price breaks upper band
                              np.where(df['Close'] < df['BB_lower'], 1, 0))  # Buy when price breaks lower band
    
    # Ichimoku Cloud signals (enhanced)
    df['Cloud_signal'] = np.where(
        # Strong bullish: Price above cloud + Conversion above Base + Green cloud
        (df['Close'] > df['Senkou_span_a']) & 
        (df['Close'] > df['Senkou_span_b']) & 
        (df['Tenkan_sen'] > df['Kijun_sen']) &
        (df['Senkou_span_a'] > df['Senkou_span_b']), 2,  # Very bullish
        np.where(
            # Moderately bullish: Price above cloud
            (df['Close'] > df['Senkou_span_a']) & 
            (df['Close'] > df['Senkou_span_b']), 1,
            np.where(
                # Very bearish: Price below cloud + Conversion below Base + Red cloud
                (df['Close'] < df['Senkou_span_a']) & 
                (df['Close'] < df['Senkou_span_b']) &
                (df['Tenkan_sen'] < df['Kijun_sen']) &
                (df['Senkou_span_a'] < df['Senkou_span_b']), -2,  # Very bearish
                np.where(
                    # Moderately bearish: Price below cloud
                    (df['Close'] < df['Senkou_span_a']) & 
                    (df['Close'] < df['Senkou_span_b']), -1,
                    0  # Neutral when price is inside the cloud
                )
            )
        )
    )
    
    # Parabolic SAR signals (enhanced)
    df['SAR_signal'] = np.where(
        # Strong bullish: Price well above SAR
        (df['Close'] > df['SAR']) & 
        (df['Close'] > df['Close'].shift(1)) &  # Upward momentum
        ((df['Close'] - df['SAR']) / df['Close'] > 0.02), 2,  # Price 2% above SAR
        np.where(
            # Moderately bullish: Price above SAR
            df['Close'] > df['SAR'], 1,
            np.where(
                # Strong bearish: Price well below SAR
                (df['Close'] < df['SAR']) &
                (df['Close'] < df['Close'].shift(1)) &  # Downward momentum
                ((df['SAR'] - df['Close']) / df['Close'] > 0.02), -2,  # Price 2% below SAR
                -1  # Moderately bearish: Price below SAR
            )
        )
    )
    
    # Combined signal (weighted majority vote with enhanced sensitivity)
    df['Combined_signal'] = np.sign(
        df['MA_signal'] * 0.15 +          # 15% weight to MA crossover
        df['MACD_signal_trend'] * 0.15 +  # 15% weight to MACD
        df['BB_signal'] * 0.1 +           # 10% weight to Bollinger Bands
        (df['Cloud_signal'] / 2) * 0.3 +  # 30% weight to Ichimoku Cloud (normalized to [-1,1])
        (df['SAR_signal'] / 2) * 0.3      # 30% weight to Parabolic SAR (normalized to [-1,1])
    )
    
    # Buy/Sell points based on signal changes
    df['Signal_change'] = df['Combined_signal'].diff()
    df['Buy_signal'] = (df['Signal_change'] == 2) | (df['Signal_change'] == 1)
    df['Sell_signal'] = (df['Signal_change'] == -2) | (df['Signal_change'] == -1)
    
    return df

def plot_trend_analysis(df):
    """Create comprehensive trend following charts"""
    fig, axes = plt.subplots(8, 1, figsize=(15, 28))  # Increased height for more plots
    fig.suptitle('Apple (AAPL) - Trend Following Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Price with Moving Averages and Buy/Sell signals
    ax1 = axes[0]
    ax1.plot(df.index, df['Close'], label='AAPL Close', linewidth=2, color='black')
    ax1.plot(df.index, df['SMA_20'], label='SMA 20', alpha=0.7, color='blue')
    ax1.plot(df.index, df['SMA_50'], label='SMA 50', alpha=0.7, color='red')
    ax1.plot(df.index, df['EMA_12'], label='EMA 12', alpha=0.7, color='green', linestyle='--')
    
    # Plot Parabolic SAR with size based on signal strength
    sar_bull = df[df['SAR_bull']]
    sar_bear = df[~df['SAR_bull']]
    
    # Strong signals (size=50), normal signals (size=30)
    strong_bull = sar_bull[sar_bull['SAR_signal'] == 2]
    normal_bull = sar_bull[sar_bull['SAR_signal'] == 1]
    strong_bear = sar_bear[sar_bear['SAR_signal'] == -2]
    normal_bear = sar_bear[sar_bear['SAR_signal'] == -1]
    
    ax1.scatter(strong_bull.index, strong_bull['SAR'], 
                color='green', marker='.', s=50, label='SAR (Strong Bullish)', alpha=0.7)
    ax1.scatter(normal_bull.index, normal_bull['SAR'], 
                color='green', marker='.', s=30, label='SAR (Bullish)', alpha=0.7)
    ax1.scatter(strong_bear.index, strong_bear['SAR'], 
                color='red', marker='.', s=50, label='SAR (Strong Bearish)', alpha=0.7)
    ax1.scatter(normal_bear.index, normal_bear['SAR'], 
                color='red', marker='.', s=30, label='SAR (Bearish)', alpha=0.7)
    
    # Plot buy/sell signals with size based on strength
    buy_signals = df[df['Buy_signal']]
    sell_signals = df[df['Sell_signal']]
    
    # Differentiate between strong and normal signals
    strong_buy = buy_signals[df['Combined_signal'] > 0.5]
    normal_buy = buy_signals[df['Combined_signal'] <= 0.5]
    strong_sell = sell_signals[df['Combined_signal'] < -0.5]
    normal_sell = sell_signals[df['Combined_signal'] >= -0.5]
    
    ax1.scatter(strong_buy.index, strong_buy['Close'], 
               color='green', marker='^', s=150, label='Strong Buy', zorder=5)
    ax1.scatter(normal_buy.index, normal_buy['Close'], 
               color='lightgreen', marker='^', s=100, label='Buy', zorder=5)
    ax1.scatter(strong_sell.index, strong_sell['Close'], 
               color='red', marker='v', s=150, label='Strong Sell', zorder=5)
    ax1.scatter(normal_sell.index, normal_sell['Close'], 
               color='lightcoral', marker='v', s=100, label='Sell', zorder=5)
    
    ax1.set_title('Price Action with Moving Averages and Signals')
    ax1.set_ylabel('Price ($)')
    ax1.legend(ncol=2, loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Bollinger Bands
    ax2 = axes[1]
    ax2.plot(df.index, df['Close'], label='AAPL Close', linewidth=2, color='black')
    ax2.plot(df.index, df['BB_upper'], label='BB Upper', alpha=0.7, color='red', linestyle='--')
    ax2.plot(df.index, df['BB_middle'], label='BB Middle', alpha=0.7, color='blue')
    ax2.plot(df.index, df['BB_lower'], label='BB Lower', alpha=0.7, color='red', linestyle='--')
    ax2.fill_between(df.index, df['BB_upper'], df['BB_lower'], alpha=0.1, color='gray')
    
    ax2.set_title('Bollinger Bands')
    ax2.set_ylabel('Price ($)')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: MACD
    ax3 = axes[2]
    ax3.plot(df.index, df['MACD'], label='MACD', linewidth=2, color='blue')
    ax3.plot(df.index, df['MACD_signal'], label='MACD Signal', linewidth=2, color='red')
    ax3.bar(df.index, df['MACD_histogram'], label='MACD Histogram', alpha=0.3, color='green')
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    ax3.set_title('MACD Indicator')
    ax3.set_ylabel('MACD')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: RSI
    ax4 = axes[3]
    ax4.plot(df.index, df['RSI'], label='RSI', color='blue', linewidth=1.5)
    ax4.axhline(y=70, color='red', linestyle='--', alpha=0.5)  # Overbought line
    ax4.axhline(y=30, color='green', linestyle='--', alpha=0.5)  # Oversold line
    ax4.fill_between(df.index, df['RSI'], 70, where=(df['RSI']>=70), color='red', alpha=0.3)  # Overbought zone
    ax4.fill_between(df.index, df['RSI'], 30, where=(df['RSI']<=30), color='green', alpha=0.3)  # Oversold zone
    ax4.set_title('Relative Strength Index (RSI)')
    ax4.set_ylabel('RSI')
    ax4.set_ylim(0, 100)
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Stochastic Oscillator
    ax5 = axes[4]
    ax5.plot(df.index, df['Stoch_K'], label='%K', color='blue', linewidth=1.5)
    ax5.plot(df.index, df['Stoch_D'], label='%D', color='red', linewidth=1.5)
    ax5.axhline(y=80, color='red', linestyle='--', alpha=0.5)  # Overbought line
    ax5.axhline(y=20, color='green', linestyle='--', alpha=0.5)  # Oversold line
    ax5.fill_between(df.index, df['Stoch_K'], 80, where=(df['Stoch_K']>=80), color='red', alpha=0.3)
    ax5.fill_between(df.index, df['Stoch_K'], 20, where=(df['Stoch_K']<=20), color='green', alpha=0.3)
    ax5.set_title('Stochastic Oscillator')
    ax5.set_ylabel('Stochastic')
    ax5.set_ylim(0, 100)
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # Plot 6: Williams %R
    ax6 = axes[5]
    ax6.plot(df.index, df['Williams_R'], label='Williams %R', color='purple', linewidth=1.5)
    ax6.axhline(y=-20, color='red', linestyle='--', alpha=0.5)  # Overbought line
    ax6.axhline(y=-80, color='green', linestyle='--', alpha=0.5)  # Oversold line
    ax6.fill_between(df.index, df['Williams_R'], -20, where=(df['Williams_R']>=-20), color='red', alpha=0.3)
    ax6.fill_between(df.index, df['Williams_R'], -80, where=(df['Williams_R']<=-80), color='green', alpha=0.3)
    ax6.set_title('Williams %R')
    ax6.set_ylabel('Williams %R')
    ax6.set_ylim(-100, 0)
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    # Plot 7: Volume Analysis
    ax7 = axes[6]
    # Plot volume bars with colors based on price movement
    colors = np.where(df['Close'] >= df['Close'].shift(1), 'green', 'red')
    ax7.bar(df.index, df['Volume'], color=colors, alpha=0.5, label='Volume')
    ax7.plot(df.index, df['Volume_SMA'], color='blue', linewidth=1.5, label='Volume SMA (20)')
    # Plot OBV on secondary y-axis
    ax7b = ax7.twinx()
    ax7b.plot(df.index, df['OBV'], color='purple', linewidth=1.5, label='OBV')
    ax7.set_title('Volume Analysis')
    ax7.set_ylabel('Volume')
    ax7b.set_ylabel('On Balance Volume (OBV)')
    # Combine legends
    lines1, labels1 = ax7.get_legend_handles_labels()
    lines2, labels2 = ax7b.get_legend_handles_labels()
    ax7b.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    ax7.grid(True, alpha=0.3)
    
    # Plot 8: Ichimoku Cloud with enhanced visualization
    ax8 = axes[7]
    
    # Plot price and Ichimoku components
    ax8.plot(df.index, df['Close'], label='Price', color='black', linewidth=1.5, zorder=5)
    ax8.plot(df.index, df['Tenkan_sen'], label='Conversion (9)', color='red', alpha=0.7)
    ax8.plot(df.index, df['Kijun_sen'], label='Base (26)', color='blue', alpha=0.7)
    ax8.plot(df.index, df['Chikou_span'], label='Lagging Span', color='green', alpha=0.7)
    
    # Plot the cloud with enhanced colors
    ax8.fill_between(df.index, df['Senkou_span_a'], df['Senkou_span_b'], 
                     where=df['Senkou_span_a'] >= df['Senkou_span_b'],
                     color='green', alpha=0.2, label='Bullish Cloud')
    ax8.fill_between(df.index, df['Senkou_span_a'], df['Senkou_span_b'], 
                     where=df['Senkou_span_a'] < df['Senkou_span_b'],
                     color='red', alpha=0.2, label='Bearish Cloud')
    
    # Add cloud boundaries
    ax8.plot(df.index, df['Senkou_span_a'], label='Leading Span A', 
             color='green', alpha=0.5, linestyle='--')
    ax8.plot(df.index, df['Senkou_span_b'], label='Leading Span B', 
             color='red', alpha=0.5, linestyle='--')
    
    # Highlight strong signals
    strong_bull_cloud = df[df['Cloud_signal'] == 2]
    strong_bear_cloud = df[df['Cloud_signal'] == -2]
    
    if len(strong_bull_cloud) > 0:
        ax8.scatter(strong_bull_cloud.index, strong_bull_cloud['Close'],
                   color='green', marker='o', s=50, label='Strong Bullish', alpha=0.7)
    if len(strong_bear_cloud) > 0:
        ax8.scatter(strong_bear_cloud.index, strong_bear_cloud['Close'],
                   color='red', marker='o', s=50, label='Strong Bearish', alpha=0.7)
    
    ax8.set_title('Ichimoku Cloud')
    ax8.set_xlabel('Date')
    ax8.set_ylabel('Price ($)')
    ax8.legend(ncol=2, loc='upper left', fontsize=8)
    ax8.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def print_recent_signals(df, days=10):
    """Print recent buy/sell signals"""
    recent_data = df.tail(days)
    recent_signals = recent_data[
        (recent_data['Buy_signal']) | (recent_data['Sell_signal'])
    ]
    
    print(f"\n--- Recent Signals (Last {days} days) ---")
    if len(recent_signals) > 0:
        for date, row in recent_signals.iterrows():
            signal_type = "BUY" if row['Buy_signal'] else "SELL"
            print(f"{date.strftime('%Y-%m-%d')}: {signal_type} at ${row['Close']:.2f}")
    else:
        print("No recent signals found.")
    
    # Current status
    current = df.iloc[-1]
    print(f"\n--- Current Status ---")
    print(f"Current Price: ${current['Close']:.2f}")
    print(f"SMA 20: ${current['SMA_20']:.2f}")
    print(f"SMA 50: ${current['SMA_50']:.2f}")
    print(f"MACD: {current['MACD']:.3f}")
    print(f"ADX (Trend Strength): {current['ADX']:.1f}")
    
    signal_status = "BULLISH" if current['Combined_signal'] > 0 else "BEARISH"
    print(f"Combined Signal: {signal_status}")

def main():
    """Main function to run the trend following analysis"""
    print("Downloading Apple data...")
    
    # Download data (you can change period: "6mo", "1y", "2y", etc.)
    aapl_data = get_apple_data(period="1y")
    
    print("Calculating trend following indicators...")
    df_with_signals = calculate_trend_signals(aapl_data)
    
    print("Creating charts...")
    plot_trend_analysis(df_with_signals)
    
    # Print recent signals and current status
    print_recent_signals(df_with_signals)
    
    # Calculate basic performance metrics
    total_signals = len(df_with_signals[df_with_signals['Buy_signal'] | df_with_signals['Sell_signal']])
    buy_signals = len(df_with_signals[df_with_signals['Buy_signal']])
    sell_signals = len(df_with_signals[df_with_signals['Sell_signal']])
    
    print(f"\n--- Signal Summary ---")
    print(f"Total signals generated: {total_signals}")
    print(f"Buy signals: {buy_signals}")
    print(f"Sell signals: {sell_signals}")

if __name__ == "__main__":
    main()
