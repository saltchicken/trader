from sqlalchemy import (
    create_engine,
    text,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy.exc import IntegrityError
import pandas as pd
import numpy as np

pd.set_option("display.float_format", "{:.2f}".format)

Base = declarative_base()


class StockTable(Base):
    __tablename__ = "stock"
    symbol = Column(String, primary_key=True)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    high_52_week = Column(Float)
    revenue_per_share_annual = Column(Float)
    three_month_average_trading_volume = Column(Float)


class StockHistoryTable(Base):
    __tablename__ = "stock_history"
    symbol = Column(String, primary_key=True)
    year = Column(Integer, primary_key=True)
    revenue_per_share = Column(Float)


class DatabaseClient:
    def __init__(self, filename):
        self.engine = create_engine(f"sqlite:///{filename}.db")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_new_column(self, table, column_name, column_type):
        self.session.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
        )

    def update_symbols(self, symbols):
        try:
            for symbol in symbols:
                row = StockTable(symbol=symbol["symbol"])
                self.session.add(row)
            self.session.commit()
            return True
        except IntegrityError:
            print("IntegrityError")
            self.session.rollback()
            return False

    def daily_update(self, symbol, metrics):
        if "52WeekHigh" not in metrics:
            metrics["52WeekHigh"] = np.nan
        if "3MonthAverageTradingVolume" not in metrics:
            metrics["3MonthAverageTradingVolume"] = np.nan

        rows_updated = (
            self.session.query(StockTable)
            .filter_by(symbol=symbol)
            .update(
                {
                    StockTable.high_52_week: metrics["52WeekHigh"],
                    StockTable.three_month_average_trading_volume: metrics[
                        "3MonthAverageTradingVolume"
                    ],
                    # `last_updated` will be auto-updated because of `onupdate=func.now()`
                },
                synchronize_session=False,
            )
        )
        if rows_updated:
            self.session.commit()
        else:
            print(f"No update: symbol '{symbol}' not found")

    # Daily
    def update_high_52_week(self, symbol, high_52_week):
        rows_updated = (
            self.session.query(StockTable)
            .filter_by(symbol=symbol)
            .update(
                {
                    StockTable.high_52_week: high_52_week
                    # `last_updated` will be auto-updated because of `onupdate=func.now()`
                },
                synchronize_session=False,
            )
        )
        if rows_updated:
            self.session.commit()
        else:
            print(f"No update: symbol '{symbol}' not found")

    # Annual
    def update_revenue_per_share_annual(self, symbol, revenue_per_share_annual):
        rows_updated = (
            self.session.query(StockTable)
            .filter_by(symbol=symbol)
            .update(
                {
                    StockTable.revenue_per_share_annual: revenue_per_share_annual
                    # `last_updated` will be auto-updated because of `onupdate=func.now()`
                },
                synchronize_session=False,
            )
        )
        if rows_updated:
            self.session.commit()
        else:
            print(f"No update: symbol '{symbol}' not found")

    def update_rps(self, symbol, year, revenue_per_share):
        try:
            row = StockHistoryTable(
                symbol=symbol, year=year, revenue_per_share=revenue_per_share
            )
            self.session.add(row)
            self.session.commit()
            return True
        except IntegrityError:
            print("IntegrityError")
            self.session.rollback()
            return False

    def update(self, symbol, year):
        try:
            # self.session.query(StockTable).filter(StockTable.symbol == symbol, StockTable.year == year).delete()
            row = StockHistoryTable(symbol=symbol, year=year)
            self.session.add(row)
            self.session.commit()
            return True
        except IntegrityError:
            print("IntegrityError")
            self.session.rollback()
            return False

    def print_table(self):
        df = pd.read_sql_table("stock", con=self.engine)
        print(df)

    def does_symbol_exist(self, symbol):
        return (
            self.session.query(StockHistoryTable)
            .filter(StockHistoryTable.symbol == symbol)
            .first()
            is not None
        )

    def does_symbol_and_year_exist(self, symbol, year):
        return (
            self.session.query(StockHistoryTable)
            .filter(StockHistoryTable.symbol == symbol, StockHistoryTable.year == year)
            .first()
            is not None
        )
