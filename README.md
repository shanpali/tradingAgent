created an initial implementation of a multi-agent stock screening tool for you.

Here's what it can do:
- It fetches live and historical stock data for Nifty 50 from Yahoo Finance.
- It calculates technical indicators: EMAs, RSI, Bollinger Bands, MACD, ATR.
- It gathers basic fundamental data: P/E, EV/EBITDA, Dividend Yield, Sector, Market Cap.
- It performs basic sentiment analysis from news headlines (if available from Yahoo Finance).
- It generates Buy/Sell signals based on a combination of technical indicators (EMA crossover, RSI, MACD).
- It calculates entry price, stop-loss (ATR-based), and target price (2:1 risk-reward).
- It ranks candidate stocks using a composite score derived from technical, fundamental (P/E for buys), and sentiment data.
- It outputs up to 5 top stock recommendations or a message if no stocks meet the stringent criteria.
- It includes error handling and I've ensured the output format and logic flow are correct.
