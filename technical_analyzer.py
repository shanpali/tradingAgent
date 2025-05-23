import yfinance as yf
import pandas as pd
import numpy as np
# Attempt to fix pandas_ta import issue with numpy.NaN
if not hasattr(np, 'NaN'):
    np.NaN = np.nan # type: ignore
import pandas_ta as ta

# Nifty 50 stocks - Yahoo Finance tickers
NIFTY_50_YAHOO_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS"
]

def fetch_and_calculate_indicators(ticker_symbol):
    """
    Fetches historical data for a ticker and calculates specified technical indicators.
    Returns a DataFrame with OHLCV data and indicators.
    """
    try:
        print(f"\nFetching historical data for {ticker_symbol}...")
        ticker_data = yf.Ticker(ticker_symbol)
        # Fetch data for a period sufficient for all indicators (e.g., 1 year for up to 26-period EMAs, 20-period BBands)
        # ATR(14) needs about 14 periods, RSI(14) needs 14, MACD(12,26,9) needs about 26+9=35 for full effect.
        # Bollinger Bands (20) needs 20. Longest is MACD. 1 year should be ample.
        
        # Fetch fundamental data from ticker.info
        info = ticker_data.info
        fundamentals = {
            'Sector': info.get('sector', 'N/A'),
            'MarketCap': info.get('marketCap', 'N/A'),
            'TrailingPE': info.get('trailingPE', 'N/A'),
            'EnterpriseToEbitda': info.get('enterpriseToEbitda', 'N/A'),
            'DividendYield': info.get('dividendYield', 'N/A'),
            'Sentiment_Score': 0, # Default neutral sentiment
            'Headlines_Sample_Str': "N/A" # Default for headlines string
        }
        print(f"Fetched fundamentals for {ticker_symbol}: Sector: {fundamentals['Sector']}, MarketCap: {fundamentals['MarketCap']}")

        # --- Sentiment Analysis from News Headlines ---
        try:
            news_items = ticker_data.news
            if news_items:
                positive_keywords = ['strong', 'growth', 'profit', 'beats', 'upgrades', 'rallies', 'positive', 'gains', 'optimistic', 'record', 'high']
                negative_keywords = ['weak', 'loss', 'falls', 'downgrades', 'slump', 'misses', 'negative', 'declines', 'pessimistic', 'concerns', 'low']
                
                all_titles = " ".join([item.get('title', '').lower() for item in news_items if item.get('title')])
                
                if all_titles.strip(): # Ensure there's content to analyze
                    positive_count = sum(keyword in all_titles for keyword in positive_keywords)
                    negative_count = sum(keyword in all_titles for keyword in negative_keywords)
                    fundamentals['Sentiment_Score'] = positive_count - negative_count
                    
                    # Store first 1-2 headlines as a concatenated string
                    headlines_to_store = [item.get('title') for item in news_items[:2] if item.get('title')]
                    if headlines_to_store:
                        fundamentals['Headlines_Sample_Str'] = "; ".join(headlines_to_store)
                    # else it remains "N/A"
                    print(f"News headlines for {ticker_symbol}: {fundamentals['Headlines_Sample_Str']}, Sentiment Score: {fundamentals['Sentiment_Score']}")
                else:
                    print(f"No valid titles found in news for {ticker_symbol}.") # Headlines_Sample_Str remains "N/A"
            else:
                print(f"No news items found for {ticker_symbol}.") # Headlines_Sample_Str remains "N/A"
        except Exception as e:
            print(f"Error fetching or processing news for {ticker_symbol}: {e}")
            # Sentiment_Score remains 0, Headlines_Sample_Str remains "N/A"

        df = ticker_data.history(period="1y")

        if df.empty:
            print(f"No historical data found for {ticker_symbol}. Skipping technical calculations.")
            # Still, we might want to return a DataFrame with just fundamentals if that's useful,
            # but current structure expects OHLC for indicators. For now, return None if no history.
            return None

        print(f"Calculating indicators for {ticker_symbol}...")
        # Calculate EMA
        df.ta.ema(length=9, append=True)  # Default column name: EMA_9
        df.ta.ema(length=21, append=True) # Default column name: EMA_21

        # Calculate RSI
        df.ta.rsi(length=14, append=True) # Default column name: RSI_14

        # Calculate Bollinger Bands
        df.ta.bbands(length=20, std=2, append=True) # Columns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0

        # Calculate MACD
        df.ta.macd(fast=12, slow=26, signal=9, append=True) # Columns: MACD_12_26_9, MACDH_12_26_9, MACDS_12_26_9

        # Calculate ATR
        df.ta.atr(length=14, append=True) # Column: ATR_14
        
        # Remove rows with NaN values that are generated at the beginning of the series due to indicator calculations
        df.dropna(inplace=True)
        
        if df.empty:
            print(f"DataFrame empty for {ticker_symbol} after indicator calculation and dropna. Skipping signal generation.")
            # If we had fundamentals, we could potentially return them, but let's stick to current flow.
            return None

        # Add fundamentals to the DataFrame (constant for all rows)
        for key, value in fundamentals.items():
            df[key] = value

        # --- Signal Generation ---
        # === REVERTED TO ORIGINAL CRITERIA ===
        print("--- Using ORIGINAL signal criteria ---")
        buy_conditions = (
            (df['EMA_9'] > df['EMA_21']) &
            (df['RSI_14'] < 40) &
            (df['MACD_12_26_9'] > df['MACDs_12_26_9'])
        )
        sell_conditions = (
            (df['EMA_9'] < df['EMA_21']) &
            (df['RSI_14'] > 60) &
            (df['MACD_12_26_9'] < df['MACDs_12_26_9'])
        )
        # === ORIGINAL CRITERIA END ===

        # Generate signals
        df['Signal'] = 'Hold'
        df.loc[buy_conditions, 'Signal'] = 'Buy'
        df.loc[sell_conditions, 'Signal'] = 'Sell'

        # --- Calculate Entry, Stop-Loss, Target for the most recent data point if signal is Buy/Sell ---
        # Initialize columns for clarity, will only be populated for the last row if signal is active
        df['Entry_Price'] = pd.NA
        df['Stop_Loss'] = pd.NA
        df['Target_Price'] = pd.NA
        df['Rank_Score'] = pd.NA # Initialize Rank_Score column

        last_row_index = df.index[-1]
        current_signal = df.loc[last_row_index, 'Signal']
        
        if current_signal in ['Buy', 'Sell']:
            # Calculate Entry, SL, TP
            entry_price = df.loc[last_row_index, 'Close']
            atr_value = df.loc[last_row_index, 'ATRr_14']
            df.loc[last_row_index, 'Entry_Price'] = entry_price
            
            stop_loss = 0.0
            if current_signal == 'Buy':
                stop_loss = entry_price - (2 * atr_value)
                target_price = entry_price + (2 * (entry_price - stop_loss))
            else: # Sell
                stop_loss = entry_price + (2 * atr_value)
                target_price = entry_price - (2 * (stop_loss - entry_price))
            
            df.loc[last_row_index, 'Stop_Loss'] = stop_loss
            df.loc[last_row_index, 'Target_Price'] = target_price

            # --- Calculate Rank Score for the last row ---
            rank_score = 0
            # Base score for signal
            if current_signal == 'Buy':
                rank_score += 2
                # RSI Confirmation for Buy
                if df.loc[last_row_index, 'RSI_14'] < 50:
                    rank_score += 1
                # Fundamental Check (P/E) for Buy
                pe_ratio = df.loc[last_row_index, 'TrailingPE']
                if isinstance(pe_ratio, (int, float)) and 0 < pe_ratio <= 30:
                    rank_score += 1
            elif current_signal == 'Sell':
                rank_score += 2 # Higher score for stronger sell signal
                # RSI Confirmation for Sell
                if df.loc[last_row_index, 'RSI_14'] > 50:
                    rank_score += 1
            
            # Sentiment Score Contribution
            sentiment_score_val = df.loc[last_row_index, 'Sentiment_Score']
            if isinstance(sentiment_score_val, (int, float)): # Ensure it's a number
                 rank_score += sentiment_score_val

            df.loc[last_row_index, 'Rank_Score'] = rank_score
        
        return df

    except Exception as e:
        print(f"Error processing {ticker_symbol}: {e}")
        return None

def main():
    print("Starting technical analysis, signal generation, and ranking for Nifty 50 stocks...")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1200) # Increased width for potentially more columns in output
    
    candidate_stocks = []

    for ticker_symbol in NIFTY_50_YAHOO_TICKERS:
        print(f"\nProcessing {ticker_symbol}...")
        df_processed = fetch_and_calculate_indicators(ticker_symbol)
        
        if df_processed is not None and not df_processed.empty:
            last_row = df_processed.iloc[-1].copy() # Use .copy() to avoid SettingWithCopyWarning
            last_row['Ticker'] = ticker_symbol # Add ticker symbol to the series for easy access
            
            if last_row['Signal'] in ['Buy', 'Sell']:
                # Ensure Rank_Score is present, default to a very low number if somehow missing
                if pd.isna(last_row.get('Rank_Score')):
                    print(f"Warning: Rank_Score not calculated for {ticker_symbol}. Defaulting to -100.")
                    last_row['Rank_Score'] = -100 
                candidate_stocks.append(last_row)
                print(f"Actionable signal '{last_row['Signal']}' for {ticker_symbol} with Rank Score: {last_row['Rank_Score']:.2f}")
            elif last_row['Signal'] == 'Hold':
                print(f"Signal for {ticker_symbol}: Hold. Not adding to recommendations.")
            else:
                print(f"No definitive signal for {ticker_symbol}.")
        else:
            print(f"Could not process data for {ticker_symbol}. Skipping.")

    # Sort candidates by Rank_Score in descending order
    candidate_stocks.sort(key=lambda x: x['Rank_Score'], reverse=True)
    
    print("\n--- Top 5 Stock Recommendations ---")
    if not candidate_stocks:
        print("No actionable trading signals found today.")
    else:
        top_5_recommendations = candidate_stocks[:5]
        for i, stock_data in enumerate(top_5_recommendations):
            print(f"\nRecommendation #{i+1}:")
            print(f"  Ticker: {stock_data['Ticker']}")
            print(f"  Signal: {stock_data['Signal']}")
            entry_price = stock_data.get('Entry_Price')
            stop_loss = stock_data.get('Stop_Loss')
            target_price = stock_data.get('Target_Price')
            print(f"  Entry Price: {entry_price:.2f}" if pd.notna(entry_price) else "  Entry Price: N/A")
            print(f"  Stop-Loss: {stop_loss:.2f}" if pd.notna(stop_loss) else "  Stop-Loss: N/A")
            print(f"  Target Price: {target_price:.2f}" if pd.notna(target_price) else "  Target Price: N/A")
            print(f"  Calculated Rank_Score: {stock_data['Rank_Score']:.2f}")
            print(f"  Last Close: {stock_data['Close']:.2f}")
            
            print("  Key Indicators:")
            print(f"    EMAs: EMA_9={stock_data['EMA_9']:.2f}, EMA_21={stock_data['EMA_21']:.2f}")
            print(f"    RSI_14: {stock_data['RSI_14']:.2f}")
            print(f"    MACD: {stock_data['MACD_12_26_9']:.2f} (Signal: {stock_data['MACDs_12_26_9']:.2f}, Hist: {stock_data['MACDh_12_26_9']:.2f})")
            pe_ratio = stock_data.get('TrailingPE', 'N/A')
            print(f"    P/E Ratio: {pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else f"    P/E Ratio: {pe_ratio}")
            print(f"    Sentiment Score: {stock_data.get('Sentiment_Score', 'N/A')}")
            headlines_str = stock_data.get('Headlines_Sample_Str', "N/A")
            if headlines_str != "N/A" and headlines_str:
                 print(f"    Recent Headlines: {headlines_str}")
            else:
                 print(f"    Recent Headlines: N/A")
    # Removed redundant "Could not process" message from here, as it's handled per ticker.

    print("\nSignal generation and analysis processing complete.")

if __name__ == "__main__":
    main()
