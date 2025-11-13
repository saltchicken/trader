use time::macros::datetime;
use trader::{Contract, Duration, Trader};

// const CONNECTION_URL: &str = "127.0.0.1:4002";
const CONNECTION_URL: &str = "127.0.0.1:7497";
const CLIENT_ID: i32 = 100;

#[tokio::main]
async fn main() {
    let trader = Trader::connect(CONNECTION_URL, CLIENT_ID)
        .await
        .expect("connection to TWS failed!");

    println!("Successfully connected to TWS at {CONNECTION_URL}");

    let contract = Contract::stock("AAPL").build();
    let end_date = Some(datetime!(2023-06-01 00:00:00 UTC));
    let duration = Duration::days(1);

    match trader
        .get_historical_data(&contract, end_date, duration)
        .await
    {
        Ok(historical_data) => {
            println!(
                "start: {:?}, end: {:?}",
                historical_data.start, historical_data.end
            );

            for bar in &historical_data.bars {
                println!("{bar:?}");
            }
        }
        Err(e) => {
            eprintln!("Error fetching historical data: {e}");
        }
    }
}
