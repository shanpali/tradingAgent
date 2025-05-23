import yfinance as yf
import pandas as pd

# Nifty 50 stocks - Yahoo Finance tickers
# Using a smaller list for brevity in example output
NIFTY_50_YAHOO_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS"
]

def fetch_stock_data_yfinance(stock_tickers):
    """
    Fetches current market price and volume for a list of stock tickers using yfinance.
    """
    data_list = []
    for ticker_symbol in stock_tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info  # Fetches a dictionary of information about the ticker

            # Determine the price:
            # 'currentPrice' is often available for actively traded stocks during market hours.
            # 'regularMarketPrice' can also be a good source.
            # 'previousClose' is a fallback if the market is closed or other prices aren't available.
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            
            volume = info.get('volume') or info.get('regularMarketVolume')

            if price is None or volume is None:
                print(f"Warning: Could not retrieve price or volume for {ticker_symbol}. Skipping.")
                data_list.append({
                    "Symbol": ticker_symbol,
                    "Price": "N/A",
                    "Volume": "N/A"
                })
                continue

            data_list.append({
                "Symbol": ticker_symbol,
                "Price": price,
                "Volume": volume
            })
            print(f"Successfully fetched data for {ticker_symbol}")

        except Exception as e:
            print(f"Error fetching data for {ticker_symbol}: {e}")
            data_list.append({
                "Symbol": ticker_symbol,
                "Price": "Error",
                "Volume": "Error"
            })
            
    return data_list

def create_dataframe(data_list):
    """
    Creates a Pandas DataFrame from the list of stock data.
    """
    if not data_list:
        return pd.DataFrame(columns=["Symbol", "Price", "Volume"])
        
    df = pd.DataFrame(data_list, columns=["Symbol", "Price", "Volume"])
    return df

def main():
    print("Fetching Nifty 50 data using yfinance...")
    
    fetched_data = fetch_stock_data_yfinance(NIFTY_50_YAHOO_TICKERS)
    
    df_nifty50 = create_dataframe(fetched_data)

    if not df_nifty50.empty:
        print("\nNifty 50 Data (from yfinance):")
        print(df_nifty50.head())
        print("\nDataFrame Structure:")
        df_nifty50.info()
    else:
        print("Could not retrieve or create data. DataFrame is empty.")

if __name__ == "__main__":
    main()
