from sqlalchemy import func, desc
from sqlalchemy.orm import aliased
from .finance_client import FinanceClient
from .database import DatabaseClient, Company, MetricSnapshot
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

from pprint import pprint

from .log import logger


class Trader:
    def __init__(self):
        self.client = FinanceClient()
        self.db = DatabaseClient("stock_data")

    def update_symbols(self):
        companies = self.client.get_all_stocks()
        new_companies = []

        for company in companies:
            if not self.db.does_symbol_exist(company["symbol"]):
                new_companies.append(company)

        if new_companies:
            logger.debug(f"Adding {len(new_companies)} new symbols.")
            self.db.update_symbols(new_companies)
        else:
            logger.debug("No new symbols to add.")

    def daily_update(self):
        if not self.is_within_allowed_update_window():
            logger.error("Not within allowed update window. Skipping.")
            return

        for symbol in self.db.get_all_symbols():
            logger.debug(symbol)
            if self.db.was_updated_in_nightly_window(symbol):
                logger.warning(
                    f"{symbol} already updated during the current nightly window. Skipping."
                )
                continue

            metrics = self.client.get_metrics(symbol)
            self.db.daily_update(symbol, metrics["metric"])

    def is_within_allowed_update_window(self):
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        if now.hour >= 18 or now.hour < 2:
            return True
        return False

    def get_latest(self, limit=10):
        subquery = (
            self.db.session.query(
                MetricSnapshot.symbol,
                func.max(MetricSnapshot.timestamp).label("latest"),
            )
            .group_by(MetricSnapshot.symbol)
            .subquery()
        )

        alias = aliased(MetricSnapshot)

        query = (
            self.db.session.query(alias.symbol, alias.month3_average_trading_volume)
            .join(
                subquery,
                (alias.symbol == subquery.c.symbol)
                & (alias.timestamp == subquery.c.latest),
            )
            .filter(alias.month3_average_trading_volume != None)
            .order_by(alias.month3_average_trading_volume.desc())
            .limit(limit)
        )

        return query.all()

    def get_snapshots_from_past_day(self):
        now_utc = datetime.now(tz=ZoneInfo("UTC"))
        one_day_ago = now_utc - timedelta(days=1)

        snapshots = (
            self.db.session.query(MetricSnapshot)
            .filter(MetricSnapshot.timestamp >= one_day_ago)
            .order_by(MetricSnapshot.timestamp.desc())
            .all()
        )

        logger.info(f"Found {len(snapshots)} snapshots from the past day.")

        # Convert to DataFrame
        df = pd.DataFrame([s.__dict__ for s in snapshots])
        # df = df.drop(columns=["_sa_instance_state"])  # Drop SQLAlchemy internal column
        return df

    def score_snapshots(self):
        df = self.get_snapshots_from_past_day()

        if df.empty:
            logger.warning("No data to score.")
            return df

        # Normalize and add scoring columns
        def normalize_metric(df, column, higher_is_better=True):
            if df[column].isnull().all():
                return pd.Series([0] * len(df))  # Avoid NaNs if whole column is null

            min_val = df[column].min()
            max_val = df[column].max()
            if max_val == min_val:
                return pd.Series([1] * len(df))  # All values are the same
            if higher_is_better:
                return (df[column] - min_val) / (max_val - min_val)
            else:
                return (max_val - df[column]) / (max_val - min_val)

        # Rename columns to match your expected inputs (if needed)
        df["peTTM"] = df["pe_ttm"]
        df["epsGrowth5Y"] = df["eps_growth_5y"]
        df["roeTTM"] = df["roe_ttm"]
        df["debtToEquity"] = df["long_term_debt_equity_quarterly"]
        df["grossMarginTTM"] = df["gross_margin_ttm"]
        df["revenueGrowth5Y"] = df["revenue_growth_5y"]
        df["pfcfShareTTM"] = df["pfcf_share_ttm"]

        # Apply score calculations
        df["score_pe"] = normalize_metric(df, "peTTM", higher_is_better=False)
        df["score_eps_growth"] = normalize_metric(df, "epsGrowth5Y", True)
        df["score_roe"] = normalize_metric(df, "roeTTM", True)
        df["score_debt"] = normalize_metric(df, "debtToEquity", False)
        df["score_margin"] = normalize_metric(df, "grossMarginTTM", True)
        df["score_revenue_growth"] = normalize_metric(df, "revenueGrowth5Y", True)
        df["score_pfcf"] = normalize_metric(df, "pfcfShareTTM", False)

        return df
