use ibapi::prelude::*;
use time::macros::datetime;

// const CONNECTION_URL: &str = "127.0.0.1:4002";
const CONNECTION_URL: &str = "127.0.0.1:7497";
const CLIENT_ID: i32 = 100;

#[tokio::main]
async fn main() {
    let client = Client::connect(CONNECTION_URL, CLIENT_ID)
        .await
        .expect("connection to TWS failed!");
    println!("Successfully connected to TWS at {CONNECTION_URL}");

    let contract = Contract::stock("AAPL").build();

    let historical_data = client
        .historical_data(
            &contract,
            Some(datetime!(2023-04-11 20:00 UTC)),
            1.days(),
            HistoricalBarSize::Hour,
            Some(HistoricalWhatToShow::Trades),
            TradingHours::Regular,
        )
        .await
        .expect("historical data request failed");

    println!(
        "start: {:?}, end: {:?}",
        historical_data.start, historical_data.end
    );

    for bar in &historical_data.bars {
        println!("{bar:?}");
    }
}
