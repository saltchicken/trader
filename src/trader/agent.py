from .database import DatabaseClient

from backtesting import Backtest

from .log import logger


class Trader:
    def __init__(self):
        self.db = DatabaseClient("stock_data")

    def get_top(self):
        companies = self.db.run_query("""
        SELECT * FROM metric_snapshots 
        WHERE pe_ttm IS NOT NULL AND 
        roe_ttm IS NOT NULL AND
        long_term_debt_equity_quarterly IS NOT NULL AND
        eps_ttm IS NOT NULL AND
        revenue_growth_5y IS NOT NULL
        ORDER BY symbol ASC
        """)
        # logger.info(f"Processing {len(companies)} companies that match filter criteria")

        # Apply filtering criteria directly to the DataFrame
        filtered_df = companies[
            (companies["pe_ttm"] > 0)
            & (companies["pe_ttm"] < 40)
            & (companies["roe_ttm"] > 0.15)
            & (companies["long_term_debt_equity_quarterly"] < 1.0)
            & (companies["revenue_growth_5y"] > 0.05)
        ]

        logger.info(f"Found {len(filtered_df)} companies matching all criteria")
        return filtered_df

    def backtest(self, symbols, strategy):
        print(f"\n🔄 Fetching data for all symbols...")
        stock_data_cache = self.db.client.get_all_stock_data(symbols)

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
        stock_data_cache = self.db.client.get_all_stock_data(symbols)
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
