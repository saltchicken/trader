from sqlalchemy import (
    create_engine,
    text,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    func,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from sqlalchemy.exc import IntegrityError
import pandas as pd
import numpy as np

pd.set_option("display.float_format", "{:.2f}".format)

from datetime import date

Base = declarative_base()

KEY_MAPPING = {
    "52WeekHigh": "week52_high",
    "3MonthAverageTradingVolume": "month3_average_trading_volume",
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
    revenue_per_share_annual = Column(Float)
    month3_average_trading_volume = Column(Float)

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
        self.engine = create_engine(f"sqlite:///{filename}.db")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    # def add_new_column(self, table, column_name, column_type):
    #     self.session.execute(
    #         text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
    #     )

    def update_symbols(self, companies):
        print(companies)
        try:
            for company in companies:
                row = Company(
                    symbol=company["symbol"], description=company["description"]
                )
                self.session.add(row)
            self.session.commit()
            return True
        except IntegrityError:
            print("IntegrityError")
            self.session.rollback()
            return False

    def daily_update(self, symbol, metrics):
        # Ensure all expected keys exist in metrics
        for key in KEY_MAPPING:
            if key not in metrics:
                print(f"Missing key: {key}")
                metrics[key] = np.nan

        # Build kwargs for MetricSnapshot constructor
        snapshot_data = {"symbol": symbol}

        for key, attr_name in KEY_MAPPING.items():
            snapshot_data[attr_name] = metrics[key]

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

    # def daily_update(self, symbol, metrics):
    #     # Ensure keys from KEY_MAPPING exist in metrics; fill with NaN if missing
    #     for key in KEY_MAPPING:
    #         if key not in metrics:
    #             metrics[key] = np.nan
    #
    #     # Build a dictionary of ORM attributes to update
    #     update_dict = {}
    #     for key, attr_name in KEY_MAPPING.items():
    #         if hasattr(MetricSnapshot, attr_name):
    #             update_dict[getattr(MetricSnapshot, attr_name)] = metrics[key]
    #
    #     rows_updated = (
    #         self.session.query(MetricSnapshot)
    #         .filter_by(symbol=symbol)
    #         .update(update_dict, synchronize_session=False)
    #     )
    #
    #     if rows_updated:
    #         self.session.commit()
    #     else:
    #         print(f"No update: symbol '{symbol}' not found")

    def was_updated_today(self, symbol):
        latest_snapshot = (
            self.session.query(MetricSnapshot)
            .filter(MetricSnapshot.symbol == symbol)
            .order_by(MetricSnapshot.timestamp.desc())
            .first()
        )
        return latest_snapshot and latest_snapshot.timestamp.date() == date.today()

    # Annual
    def update_revenue_per_share_annual(self, symbol, revenue_per_share_annual):
        rows_updated = (
            self.session.query(MetricSnapshot)
            .filter_by(symbol=symbol)
            .update(
                {
                    MetricSnapshot.revenue_per_share_annual: revenue_per_share_annual
                    # `last_updated` will be auto-updated because of `onupdate=func.now()`
                },
                synchronize_session=False,
            )
        )
        if rows_updated:
            self.session.commit()
        else:
            print(f"No update: symbol '{symbol}' not found")

    def print_table(self, table):
        df = pd.read_sql_table(table, con=self.engine)
        print(df)

    def does_symbol_exist(self, symbol):
        return (
            self.session.query(Company).filter(Company.symbol == symbol).first()
            is not None
        )

    def get_all_symbols(self):
        return [row.symbol for row in self.session.query(Company.symbol).all()]
