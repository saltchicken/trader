use iso_currency::Currency as IsoCurrency;
use paft_money::currency::Currency as PaftCurrency;

use trader::Trader;

// const CONNECTION_URL: &str = "127.0.0.1:4002";
const CONNECTION_URL: &str = "127.0.0.1:7497";
const CLIENT_ID: i32 = 100;

#[tokio::main]
async fn main() {
    let trader = Trader::connect(CONNECTION_URL, CLIENT_ID)
        .await
        .expect("connection to TWS failed!");

    println!("Successfully connected to TWS at {CONNECTION_URL}");
}
