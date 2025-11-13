use ibapi::market_data::historical::HistoricalData;
use ibapi::orders::{BracketOrderIds, OrderId};
use ibapi::prelude::*;
use time::OffsetDateTime;

pub use ibapi::market_data::historical::Duration;
pub use ibapi::prelude::Contract;
pub use ibapi::{Client, Error};

/// Represents an active connection to TWS/Gateway.
pub struct Trader {
    client: Client,
}

impl Trader {
    /// Connects to the TWS/Gateway.
    ///
    /// # Arguments
    ///
    /// * `url` - The connection string (e.g., "127.0.0.1:7497").
    /// * `client_id` - The client ID to use for the connection.
    pub async fn connect(url: &str, client_id: i32) -> Result<Self, Error> {
        let client = Client::connect(url, client_id).await?;
        Ok(Self { client })
    }

    /// Fetches historical data for a given contract.
    pub async fn get_historical_data(
        &self,
        contract: &Contract,
        end_date: Option<OffsetDateTime>,
        duration: Duration,
    ) -> Result<HistoricalData, Error> {
        self.client
            .historical_data(
                contract,
                end_date,
                duration,
                HistoricalBarSize::Hour,
                Some(HistoricalWhatToShow::Trades),
                TradingHours::Regular,
            )
            .await
    }

    /// A simple getter for the client if needed for other operations.
    pub fn client(&self) -> &Client {
        &self.client
    }

    pub async fn buy_market_order(
        &self,
        contract: &Contract,
        quantity: i32,
    ) -> Result<OrderId, Error> {
        self.client
            .order(contract)
            .buy(quantity)
            .market()
            .submit()
            .await
    }

    pub async fn sell_market_order(
        &self,
        contract: &Contract,
        quantity: i32,
    ) -> Result<OrderId, Error> {
        self.client
            .order(contract)
            .sell(quantity)
            .market()
            .submit()
            .await
    }

    pub async fn buy_bracket_order(
        &self,
        contract: &Contract,
        quantity: i32,
        entry_limit: f64,
        take_profit: f64,
        stop_loss: f64,
    ) -> Result<BracketOrderIds, Error> {
        self.client
            .order(contract)
            .buy(quantity)
            .bracket()
            .entry_limit(entry_limit)
            .take_profit(take_profit)
            .stop_loss(stop_loss)
            .submit_all()
            .await
    }
}
