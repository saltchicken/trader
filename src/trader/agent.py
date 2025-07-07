from .database import DatabaseClient, CurrentMetrics
from .external_api import AlpacaClient

from backtesting import Backtest
from datetime import datetime, timedelta, timezone

from .log import logger

# df = self.get_top()
# companies = df["symbol"].to_list()


class Trader:
    def __init__(self):
        self.db = DatabaseClient("stock_data")
        self.alpaca = AlpacaClient()

    def calculate_composite_score(self, symbol):
        company = self.db.run_query("""
WITH latest AS (
        SELECT symbol, MAX(timestamp) AS latest_timestamp
        FROM metric_snapshots
        GROUP BY symbol
        )
    SELECT *
    FROM metric_snapshots ms
    JOIN latest l ON ms.symbol = l.symbol AND ms.timestamp = l.latest_timestamp
    WHERE pe_ttm IS NOT NULL AND 
        roe_ttm IS NOT NULL AND
        long_term_debt_equity_quarterly IS NOT NULL AND
        eps_ttm IS NOT NULL AND
        revenue_growth_5y IS NOT NULL
    ORDER BY ms.symbol ASC
        """)

        if company.empty:
            logger.warning(f"No data to calculate composite score for {symbol}.")
            return 0.0  # Default to neutral score if no data

        # Create ranking for each metric (lower rank is better)
        company["pe_rank"] = company["pe_ttm"].rank(
            method="min", ascending=True, pct=True
        )  # Lower PE is better
        company["roe_rank"] = company["roe_ttm"].rank(
            method="min", ascending=False, pct=True
        )  # Higher ROE is better
        company["debt_rank"] = company["long_term_debt_equity_quarterly"].rank(
            method="min", ascending=True, pct=True
        )  # Lower debt is better
        company["growth_rank"] = company["revenue_growth_5y"].rank(
            method="min", ascending=False, pct=True
        )  # Higher growth is better

        # Calculate composite score (lower is better)
        company["composite_score"] = (
            company["pe_rank"] * 0.25
            + company["roe_rank"] * 0.25
            + company["debt_rank"] * 0.25
            + company["growth_rank"] * 0.25
        )

        row = company[company["symbol"] == symbol]
        if row.empty:
            logger.warning(f"No data to calculate composite score for {symbol}.")
            return 0.0  # Default to neutral score if no data
        # Sort by composite score (ascending = better rank)
        # sorted_companies = companies.sort_values("composite_score")

        # logger.info(f"Ranked {len(sorted_companies)} companies by composite score")
        # print(f"len company: {len(company)}")
        score = float(row["composite_score"].iloc[0])
        score = score * 2 - 1  # Normalize to [-1, 1]

        return score

    def calculate_cross_score(self, symbol, cutoff=14):
        # TODO: Determine how many days_back are needed with given cutoff
        data = self.alpaca.get_all_stock_data([symbol], days_back=730)
        df = data[symbol]
        if df is None:
            logger.warning(f"No data for {symbol}")
            return 0.0  # Default to neutral score if no data
        df = self.calculate_indicators(df)
        bullish_macd, bearish_macd, golden_cross, death_cross = self.find_crosses(df)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=cutoff)
        bullish_macd_recent = bullish_macd[bullish_macd.index >= cutoff]
        bearish_macd_recent = bearish_macd[bearish_macd.index >= cutoff]
        golden_cross_recent = golden_cross[golden_cross.index >= cutoff]
        death_cross_recent = death_cross[death_cross.index >= cutoff]
        bullish_count = len(bullish_macd_recent)
        bearish_count = len(bearish_macd_recent)
        golden_count = len(golden_cross_recent)
        death_count = len(death_cross_recent)
        total_count = bullish_count + bearish_count + golden_count + death_count
        # print(
        #     f"Total count: {total_count} | Bullish: {bullish_count} | Bearish: {bearish_count} | Golden: {golden_count} | Death: {death_count}"
        # )
        if total_count == 0:
            return 0.0
        bullish_score = bullish_count / total_count
        bearish_score = bearish_count / total_count
        golden_score = golden_count / total_count
        death_score = death_count / total_count
        cross_score = (bullish_score + golden_score) - (bearish_score + death_score)
        return cross_score

    def calculate_week52_score(self, symbol):
        sql = """
        SELECT week52_high, week52_low
        FROM metric_snapshots
        WHERE symbol = :symbol
        ORDER BY timestamp DESC
        LIMIT 1
        """
        result = self.db.run_query(sql, {"symbol": symbol})
        if result.empty:
            return 0.0  # Default to neutral score if no data

        high = result["week52_high"].values[0]
        low = result["week52_low"].values[0]
        print(f"High: {high}, Low: {low}")

        spread = high - low
        if spread == 0:
            return 0.0  # Avoid division by zero

        exchange_info = self.alpaca.get_stock_current_price(symbol)
        current_price = exchange_info[symbol].ask_price
        if current_price == 0.0:
            return 0.0  # Default to neutral score if price is zero
        if current_price is None:
            return 0.0  # Default to neutral score if no price data

        position = float((current_price - low) / spread)
        score = position * -2 + 1  # Normalize to [-1, 1]
        return score

    def update_metric_score(self, symbol, score_data):
        """Update scores in the CurrentMetrics table

        Args:
            symbol: Stock symbol
            score_data: Dict with score values (e.g., {'week52_score': 0.85})
        """
        current = self.db.session.query(CurrentMetrics).filter_by(symbol=symbol).first()

        if not current:
            current = CurrentMetrics(symbol=symbol)
            self.db.session.add(current)

        # Update fields from the provided score_data
        for field, value in score_data.items():
            if hasattr(current, field):
                setattr(current, field, value)

        self.db.session.commit()

    # Example usage
    def calculate_and_update_scores(self, symbol):
        # Calculate your scores
        week52_score = self.calculate_week52_score(symbol)
        print(f"Week 52 Score: {week52_score}")
        cross_score = self.calculate_cross_score(symbol)
        print(f"Cross Score: {cross_score}")
        composite_score = self.calculate_composite_score(symbol)
        print(f"Composite Score: {composite_score}")

        # Update the CurrentMetrics table
        self.update_metric_score(
            symbol,
            {
                "week52_score": week52_score,
                "cross_score": cross_score,
                "metrics_composite_score": composite_score,
            },
        )

    def calculate_indicators(self, df):
        # MACD
        df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

        # Moving Averages
        df["sma_50"] = df["Close"].rolling(window=50).mean()
        df["sma_200"] = df["Close"].rolling(window=200).mean()

        return df

    def find_crosses(self, df):
        # MACD Crosses
        bullish_macd = (df["macd"].shift(1) < df["signal"].shift(1)) & (
            df["macd"] > df["signal"]
        )
        bearish_macd = (df["macd"].shift(1) > df["signal"].shift(1)) & (
            df["macd"] < df["signal"]
        )

        # Golden/Death Crosses
        golden_cross = (df["sma_50"].shift(1) < df["sma_200"].shift(1)) & (
            df["sma_50"] > df["sma_200"]
        )
        death_cross = (df["sma_50"].shift(1) > df["sma_200"].shift(1)) & (
            df["sma_50"] < df["sma_200"]
        )

        return df[bullish_macd], df[bearish_macd], df[golden_cross], df[death_cross]

    def get_crosses(self, symbols):
        data = self.alpaca.get_all_stock_data(symbols, days_back=730)
        results = {}
        for symbol in symbols:
            df = data[symbol]
            df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
            df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
            df["macd"] = df["ema_12"] - df["ema_26"]
            df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

            # Moving Averages
            df["sma_50"] = df["Close"].rolling(window=50).mean()
            df["sma_200"] = df["Close"].rolling(window=200).mean()

            today = df.iloc[-1]
            yesterday = df.iloc[-2]

            # Check for MACD cross today
            bullish_macd_today = (yesterday["macd"] < yesterday["signal"]) and (
                today["macd"] > today["signal"]
            )
            bearish_macd_today = (yesterday["macd"] > yesterday["signal"]) and (
                today["macd"] < today["signal"]
            )

            # Check for Golden/Death cross today
            golden_cross_today = (yesterday["sma_50"] < yesterday["sma_200"]) and (
                today["sma_50"] > today["sma_200"]
            )
            death_cross_today = (yesterday["sma_50"] > yesterday["sma_200"]) and (
                today["sma_50"] < today["sma_200"]
            )

            result = {
                "bullish_macd": bullish_macd_today,
                "bearish_macd": bearish_macd_today,
                "golden_cross": golden_cross_today,
                "death_cross": death_cross_today,
            }
            results[symbol] = result
        return results

    def interpret_crosses(self, crosses):
        for cross, value in crosses.items():
            if cross == "bullish_macd" and value:
                return "buy"
            elif cross == "bearish_macd" and value:
                return "sell"
            elif cross == "golden_cross" and value:
                return "buy"
            elif cross == "death_cross" and value:
                return "sell"
            else:
                return "hold"

    def get_snapshots_from_past_day(self):
        return self.db.run_query(
            """
            SELECT * FROM metric_snapshots 
            WHERE timestamp >= NOW() - INTERVAL '1 day'
            """
        )

    def get_top(self):
        companies = self.db.run_query("""
WITH latest AS (
        SELECT symbol, MAX(timestamp) AS latest_timestamp
        FROM metric_snapshots
        GROUP BY symbol
        )
    SELECT *
    FROM metric_snapshots ms
    JOIN latest l ON ms.symbol = l.symbol AND ms.timestamp = l.latest_timestamp
    WHERE pe_ttm IS NOT NULL AND 
        roe_ttm IS NOT NULL AND
        long_term_debt_equity_quarterly IS NOT NULL AND
        eps_ttm IS NOT NULL AND
        revenue_growth_5y IS NOT NULL
    ORDER BY ms.symbol ASC
        """)

        # Create ranking for each metric (lower rank is better)
        companies["pe_rank"] = companies["pe_ttm"].rank(
            method="min", ascending=True
        )  # Lower PE is better
        companies["roe_rank"] = companies["roe_ttm"].rank(
            method="min", ascending=False
        )  # Higher ROE is better
        companies["debt_rank"] = companies["long_term_debt_equity_quarterly"].rank(
            method="min", ascending=True
        )  # Lower debt is better
        companies["growth_rank"] = companies["revenue_growth_5y"].rank(
            method="min", ascending=False
        )  # Higher growth is better

        # Calculate composite score (lower is better)
        companies["composite_score"] = (
            companies["pe_rank"] * 0.25
            + companies["roe_rank"] * 0.25
            + companies["debt_rank"] * 0.25
            + companies["growth_rank"] * 0.25
        )

        # Sort by composite score (ascending = better rank)
        sorted_companies = companies.sort_values("composite_score")

        logger.info(f"Ranked {len(sorted_companies)} companies by composite score")
        return sorted_companies

    def filter_bad_investments(self, df):
        filtered_df = df[
            (df["pe_ttm"] > 0)
            & (df["pe_ttm"] < 40)
            & (df["roe_ttm"] > 0.15)
            & (df["long_term_debt_equity_quarterly"] < 1.0)
            & (df["revenue_growth_5y"] > 0.05)
        ]
        return filtered_df

    def backtest(self, symbols, strategy):
        print(f"\n🔄 Fetching data for all symbols...")
        stock_data_cache = self.alpaca.get_all_stock_data(symbols)

        if stock_data_cache is None:
            print("❌ Failed to fetch stock data. Exiting.")
            return

        # Count successful downloads
        successful_symbols = [s for s in symbols if stock_data_cache.get(s) is not None]
        print(
            f"✅ Successfully loaded data for {len(successful_symbols)} out of {len(symbols)} symbols"
        )

        for symbol in symbols:
            data = stock_data_cache.get(symbol)
            if data is None:
                print(f"\n⏭️ Skipping {symbol} - no data available")
                continue

            print(f"\n🎯 ANALYZING {symbol}")
            print("-" * 40)

            print(f"\n{'=' * 60}")
            print(f"🔍 Running {strategy.__name__} for {symbol}")
            print(f"{'=' * 60}")
            result = self.run_backtest(symbol, strategy, data)
            print(f"\n📈 Backtest Results for {symbol}:")
            print(f"   Total Return:     {result['Return [%]']:.2f}%")
            print(f"   Buy & Hold:       {result['Buy & Hold Return [%]']:.2f}%")
            print(f"   Sharpe Ratio:     {result['Sharpe Ratio']:.2f}")
            print(f"   Max Drawdown:     {result['Max. Drawdown [%]']:.2f}%")
            print(f"   Number of Trades: {result['# Trades']}")

            if result["# Trades"] > 0:
                print(f"   Win Rate:         {result['Win Rate [%]']:.1f}%")
                print(f"   Avg Trade:        {result['Avg. Trade [%]']:.2f}%")

    def backtest_optimize(self, symbols, strategy):
        # Only run optimization if we have AAPL data
        stock_data_cache = self.alpaca.get_all_stock_data(symbols)
        for symbol in symbols:
            data = stock_data_cache.get(symbol)
            if data is not None:
                try:
                    opt_result = self.run_backtest(
                        symbol,
                        strategy,
                        data,
                        volume_threshold=[1.5, 1.6, 1.4, 2.0, 2.5, 3.0],
                        volume_period=[14, 15, 16, 17, 18, 19, 20, 25],
                        hold_days=[3, 5, 7, 10],
                    )

                    if opt_result is not None:
                        print(f"\n🎯 Optimized Parameters for {symbol}:")
                        strategy_instance = opt_result._strategy
                        print(
                            f"   Volume Threshold: {strategy_instance.volume_threshold}"
                        )
                        print(f"   Volume Period:    {strategy_instance.volume_period}")
                        print(f"   Hold Days:        {strategy_instance.hold_days}")
                        print(f"   Optimized Return: {opt_result['Return [%]']:.2f}%")

                except Exception as e:
                    print(f"❌ Optimization failed: {e}")
            else:
                print(f"⏭️ Skipping optimization - {symbol} data not available")

            print(f"\n✅ Analysis complete!")

    def run_backtest(self, symbol, strategy, data, **kwargs):
        """Run backtest for a given symbol and strategy"""

        try:
            bt = Backtest(data, strategy, cash=100000, commission=0.002)

            # Run backtest
            if not kwargs:
                print("📊 Running backtest...")
                result = bt.run()
            else:
                print("🔧 Optimizing parameters...")
                result = bt.optimize(**kwargs, maximize="Sharpe Ratio", max_tries=20)

            return result

        except Exception as e:
            print(f"❌ Error running backtest for {symbol}: {e}")
            print(f"   Error type: {type(e).__name__}")
            return None

    # def score_snapshots(self):
    #     df = self.get_snapshots_from_past_day()
    #
    #     if df.empty:
    #         logger.warning("No data to score.")
    #         return df
    #
    #     # Normalize and add scoring columns
    #     def normalize_metric(df, column, higher_is_better=True):
    #         if df[column].isnull().all():
    #             return pd.Series([0] * len(df))  # Avoid NaNs if whole column is null
    #
    #         min_val = df[column].min()
    #         max_val = df[column].max()
    #         if max_val == min_val:
    #             return pd.Series([1] * len(df))  # All values are the same
    #         if higher_is_better:
    #             return (df[column] - min_val) / (max_val - min_val)
    #         else:
    #             return (max_val - df[column]) / (max_val - min_val)
    #
    #     # Rename columns to match your expected inputs (if needed)
    #     df["peTTM"] = df["pe_ttm"]
    #     df["epsGrowth5Y"] = df["eps_growth_5y"]
    #     df["roeTTM"] = df["roe_ttm"]
    #     df["debtToEquity"] = df["long_term_debt_equity_quarterly"]
    #     df["grossMarginTTM"] = df["gross_margin_ttm"]
    #     df["revenueGrowth5Y"] = df["revenue_growth_5y"]
    #     df["pfcfShareTTM"] = df["pfcf_share_ttm"]
    #
    #     # Apply score calculations
    #     df["score_pe"] = normalize_metric(df, "peTTM", higher_is_better=False)
    #     df["score_eps_growth"] = normalize_metric(df, "epsGrowth5Y", True)
    #     df["score_roe"] = normalize_metric(df, "roeTTM", True)
    #     df["score_debt"] = normalize_metric(df, "debtToEquity", False)
    #     df["score_margin"] = normalize_metric(df, "grossMarginTTM", True)
    #     df["score_revenue_growth"] = normalize_metric(df, "revenueGrowth5Y", True)
    #     df["score_pfcf"] = normalize_metric(df, "pfcfShareTTM", False)
    #
    #     return df
    #
    # def composite_score(self, df):
    #     df["composite_score"] = (
    #         0.15 * df["score_pe"]
    #         + 0.15 * df["score_eps_growth"]
    #         + 0.15 * df["score_roe"]
    #         + 0.1 * df["score_debt"]
    #         + 0.15 * df["score_margin"]
    #         + 0.15 * df["score_revenue_growth"]
    #         + 0.15 * df["score_pfcf"]
    #     )
    #     df["rating"] = (df["composite_score"] * 100).round(1)
    #     df = df.sort_values("rating", ascending=False)
    #     return df

    # def get_top_by_metric(self, metric_name, limit=5):
    #     """Get top symbols by a specific metric score from latest snapshots"""
    #     df = self.score_snapshots()
    #
    #     if df.empty:
    #         logger.warning(f"No data to get top {metric_name}.")
    #         return df
    #
    #     # Keep only the latest snapshot for each symbol
    #     latest_snapshots = (
    #         df.sort_values("timestamp").groupby("symbol").last().reset_index()
    #     )
    #
    #     # Sort by the specified metric and get top results
    #     top_results = latest_snapshots.nlargest(limit, metric_name)
    #     return top_results
