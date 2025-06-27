from sqlalchemy import create_engine, text, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy.exc import IntegrityError
import pandas as pd

Base = declarative_base()

class StockTable(Base):
    __tablename__ = "stock"
    symbol = Column(String, primary_key=True)
    year = Column(Integer, primary_key=True)
    revenue_per_share = Column(Float)

class DatabaseClient:
    def __init__(self, filename):
        self.engine = create_engine(f"sqlite:///{filename}.db")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def update_rps(self, symbol, year, revenue_per_share):
        try:
            row = StockTable(symbol=symbol, year=year, revenue_per_share=revenue_per_share)
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
        return self.session.query(StockTable).filter(StockTable.symbol == symbol).first() is not None

    def does_symbol_and_year_exist(self, symbol, year):
        return self.session.query(StockTable).filter(StockTable.symbol == symbol, StockTable.year == year).first() is not None
