from finance_client import FinanceClient
from database import DatabaseClient, Company
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pprint import pprint

from log import logger

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
        print("hello")
        # if not self.is_within_allowed_update_window():
        #     logger.error("Not within allowed update window. Skipping.")
        #     return

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

