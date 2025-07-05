from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    func,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import text

from sqlalchemy.exc import IntegrityError
import pandas as pd
import numpy as np


from datetime import date
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os


from .log import logger
from .finance_client import FinanceClient

pd.set_option("display.float_format", "{:.2f}".format)

load_dotenv()
pg_user = os.getenv("PG_USER")
pg_pass = os.getenv("PG_PASS")
pg_host = os.getenv("PG_HOST", "localhost")
pg_port = os.getenv("PG_PORT", "5432")
pg_db = os.getenv("PG_DB")

Base = declarative_base()

# core_metrics = [
#     "52WeekHigh", "52WeekLow", "3MonthAverageTradingVolume", "beta",
#     "epsTTM", "epsGrowth5Y", "revenueGrowth5Y", "focfCagr5Y",
#     "netProfitMarginTTM", "grossMarginTTM", "operatingMarginTTM",
#     "roeTTM", "roaTTM", "roiTTM", "cashFlowPerShareTTM",
#     "peTTM", "pfcfShareTTM", "psTTM", "pbTTM",
#     "currentDividendYieldTTM", "dividendGrowthRate5Y", "payoutRatioTTM",
#     "longTermDebt/equityQuarterly", "currentRatioQuarterly"
# ]

KEY_MAPPING = {
    "52WeekHigh": "week52_high",
    "52WeekHighDate": "week52_high_date",
    "52WeekLow": "week52_low",
    "3MonthAverageTradingVolume": "month3_average_trading_volume",
    "dividendPerShareTTM": "dividend_per_share_ttm",
    "10DayAverageTradingVolume": "day10_average_trading_volume",
    "beta": "beta",
    "epsTTM": "eps_ttm",
    "epsGrowth5Y": "eps_growth_5y",
    "revenueGrowth5Y": "revenue_growth_5y",
    "focfCagr5Y": "focf_cagr_5y",
    "netProfitMarginTTM": "net_profit_margin_ttm",
    "grossMarginTTM": "gross_margin_ttm",
    "operatingMarginTTM": "operating_margin_ttm",
    "roeTTM": "roe_ttm",
    "roaTTM": "roa_ttm",
    "roiTTM": "roi_ttm",
    "cashFlowPerShareTTM": "cash_flow_per_share_ttm",
    "peTTM": "pe_ttm",
    "pfcfShareTTM": "pfcf_share_ttm",
    "psTTM": "ps_ttm",
    "pbTTM": "pb_ttm",
    "currentDividendYieldTTM": "current_dividend_yield_ttm",
    "dividendGrowthRate5Y": "dividend_growth_rate_5y",
    "payoutRatioTTM": "payout_ratio_ttm",
    "longTermDebt/equityQuarterly": "long_term_debt_equity_quarterly",
    "currentRatioQuarterly": "current_ratio_quarterly",
}


class Company(Base):
    __tablename__ = "companies"

    symbol = Column(String, primary_key=True)
    description = Column(String)

    snapshots = relationship("MetricSnapshot", back_populates="company")
    current_metrics = relationship(
        "CurrentMetrics", back_populates="company", uselist=False
    )


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, ForeignKey("companies.symbol"), nullable=False)
    timestamp = Column(DateTime, default=func.now())
    # last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    week52_high = Column(Float)
    week52_high_date = Column(Date)
    week52_low = Column(Float)
    month3_average_trading_volume = Column(Float)
    dividend_per_share_ttm = Column(Float)
    day10_average_trading_volume = Column(Float)
    beta = Column(Float)
    eps_ttm = Column(Float)
    eps_growth_5y = Column(Float)
    revenue_growth_5y = Column(Float)
    focf_cagr_5y = Column(Float)
    net_profit_margin_ttm = Column(Float)
    gross_margin_ttm = Column(Float)
    operating_margin_ttm = Column(Float)
    roe_ttm = Column(Float)
    roa_ttm = Column(Float)
    roi_ttm = Column(Float)
    cash_flow_per_share_ttm = Column(Float)
    pe_ttm = Column(Float)
    pfcf_share_ttm = Column(Float)
    ps_ttm = Column(Float)
    pb_ttm = Column(Float)
    current_dividend_yield_ttm = Column(Float)
    dividend_growth_rate_5y = Column(Float)
    payout_ratio_ttm = Column(Float)
    long_term_debt_equity_quarterly = Column(Float)
    current_ratio_quarterly = Column(Float)

    company = relationship("Company", back_populates="snapshots")


class CurrentMetrics(Base):
    __tablename__ = "current_metrics"

    symbol = Column(String, ForeignKey("companies.symbol"), primary_key=True)
    timestamp = Column(DateTime, default=func.now())  # when the snapshot was recorded

    week52_high = Column(Float)
    revenue_per_share_annual = Column(Float)
    month3_average_trading_volume = Column(Float)

    company = relationship("Company", back_populates="current_metrics")


class DatabaseClient:
    def __init__(self, filename):
        self.client = FinanceClient()
        self.engine = create_engine(
            f"postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def run_query(self, query):
        query = text(query)
        rows = self.session.execute(query)
        data = [dict(row._mapping) for row in rows]
        df = pd.DataFrame(data)
        return df

    def was_updated_in_nightly_window(self, symbol):
        now = datetime.now(ZoneInfo("America/Los_Angeles"))

        # Determine the 6PM start time
        if (
            now.hour < 2
        ):  # Early morning (e.g., 1AM on June 29 → window started June 28, 6PM)
            window_start = (now - timedelta(days=1)).replace(
                hour=18, minute=0, second=0, microsecond=0
            )
        else:  # Evening of the same day
            window_start = now.replace(hour=18, minute=0, second=0, microsecond=0)

        window_end = window_start + timedelta(hours=8)  # Up to 2AM next day

        # Convert to UTC for database query
        start_utc = window_start.astimezone(ZoneInfo("UTC"))
        end_utc = window_end.astimezone(ZoneInfo("UTC"))

        # Check if symbol has already been updated during this window
        return (
            self.session.query(MetricSnapshot)
            .filter(
                MetricSnapshot.symbol == symbol,
                MetricSnapshot.timestamp >= start_utc,
                MetricSnapshot.timestamp < end_utc,
            )
            .first()
            is not None
        )

    def update_symbols(self, companies):
        companies = self.client.get_all_stocks()
        new_companies = []

        for company in companies:
            if not self.does_symbol_exist(company["symbol"]):
                new_companies.append(company)

        if new_companies:
            logger.debug(f"Adding {len(new_companies)} new symbols.")

            try:
                for company in companies:
                    row = Company(
                        symbol=company["symbol"], description=company["description"]
                    )
                    self.session.add(row)
                self.session.commit()
                return True
            except IntegrityError:
                logger.error("IntegrityError")
                self.session.rollback()
                return False
        else:
            logger.debug("No new symbols to add.")
            return True

    def is_within_allowed_update_window(self):
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        if now.hour >= 18 or now.hour < 2:
            return True
        return False

    def daily_update(self):
        if not self.is_within_allowed_update_window():
            logger.error("Not within allowed update window. Skipping.")
            return

        for symbol in self.get_all_symbols():
            logger.debug(symbol)
            if self.was_updated_in_nightly_window(symbol):
                logger.warning(
                    f"{symbol} already updated during the current nightly window. Skipping."
                )
                continue

            metrics = self.client.get_metrics(symbol)
            if metrics:
                self.update_symbol(symbol, metrics["metric"])
            else:
                logger.error("There was an error. Skipping")

    def update_symbol(self, symbol, metrics):
        # Ensure all expected keys exist in metrics
        for key in KEY_MAPPING:
            if key not in metrics:
                logger.warning(f"Missing key: {key}")
                metrics[key] = np.nan

        # Build kwargs for MetricSnapshot constructor
        snapshot_data = {"symbol": symbol}

        for key, attr_name in KEY_MAPPING.items():
            value = metrics[key]
            if key == "52WeekHighDate":
                if isinstance(value, str):
                    try:
                        value = datetime.strptime(value, "%Y-%m-%d").date()
                    except ValueError:
                        logger.error(f"Invalid date format for 52WeekHighDate: {value}")
                        value = None
                elif isinstance(value, datetime):
                    value = value.date()
                elif not isinstance(value, date):
                    logger.error(
                        f"Unexpected type for 52WeekHighDate: {type(value)} This is bad"
                    )
                    value = None  # fallback for unexpected types

            snapshot_data[attr_name] = value

        # Optionally add timestamp if you want to specify it:
        # snapshot_data["timestamp"] = some_datetime_object

        snapshot = MetricSnapshot(**snapshot_data)
        self.session.add(snapshot)
        self.session.commit()

    def update_current_metrics(self, symbol, metrics):
        for key in KEY_MAPPING:
            if key not in metrics:
                metrics[key] = np.nan

        current = self.session.query(CurrentMetrics).filter_by(symbol=symbol).first()

        if not current:
            current = CurrentMetrics(symbol=symbol)
            self.session.add(current)

        for key, attr_name in KEY_MAPPING.items():
            setattr(current, attr_name, metrics[key])

        current.timestamp = func.now()
        self.session.commit()

    def does_symbol_exist(self, symbol):
        return (
            self.session.query(Company).filter(Company.symbol == symbol).first()
            is not None
        )

    def get_all_symbols(self):
        return [row.symbol for row in self.session.query(Company.symbol).all()]
