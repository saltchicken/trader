use iso_currency::Currency as IsoCurrency;
use paft_money::currency::Currency as PaftCurrency;

#[tokio::main]
async fn main() {
    let client = yfinance_rs::YfClient::default();

    // 2. Create a Ticker object for Apple
    let ticker = yfinance_rs::Ticker::new(&client, "GOOG");

    let statements = ticker.income_stmt(None).await.unwrap();

    println!("--- Annual Revenue for GOOG ---");

    // 4. Iterate over the reports and print the revenue
    for report in statements {
        println!("Fiscal Year Ending: {}", report.period);
        if let Some(total_revenue) = report.total_revenue {
            let currency = total_revenue.currency();
            match currency {
                &PaftCurrency::Iso(iso_code) => {
                    if iso_code != IsoCurrency::USD {
                        println!("   ‼️ WARNING: Currency is {:?}, not USD.", iso_code);
                    }
                }
                _ => {
                    println!(
                        "   ‼️ WARNING: Currency is not an ISO standard currency: {:?}",
                        currency
                    );
                }
            }
            println!(
                "   Total Revenue: ${:?} | Currency: {:?}",
                total_revenue.amount(),
                total_revenue.currency(),
            );
            if let Some(gross_profit) = report.gross_profit {
                println!(
                    "   Gross Profit: ${:?} | Currency: {:?}",
                    gross_profit.amount(),
                    gross_profit.currency()
                );
            }
            if let Some(net_income) = report.net_income {
                println!(
                    "   Net Income: ${:?} | Currency: {:?}",
                    net_income.amount(),
                    net_income.currency()
                );
            }
            if let Some(operating_income) = report.operating_income {
                println!(
                    "   Operating Income: ${:?} | Currency: {:?}",
                    operating_income.amount(),
                    operating_income.currency()
                );
            }
        };
    }
}
