# 📊 Supertrend Channel + 5WMA – Live Trading System

This repository contains the code for a **live trading system** based on **trend reversion** using the **Supertrend Channel** along with **5-period Weighted Moving Average (5WMA)**.

### ⚠️ Disclaimer

> This is a **live trading system project** meant for educational and research purposes.
> **No guarantees of profitability or alpha** are made — please use with caution and at your own risk.

### 🛠 Requirements

* A valid **Zerodha API Key** (Kite Connect) is needed to run the system.
* A working **PostgreSQL database** instance to store OHLC data and trade logs.
* Installation dependencies are listed in `requirements.txt`.

### 📁 Code Structure

#### `data_main.py`

* Handles **tick-by-tick live market data** using WebSocket.
* Converts ticks into **1-minute and 5-minute OHLC candles**.
* Performs better than fetching historical candles post-formation, which often involves latency.

#### `strategy_checker.py`

* Monitors the SQL database for completed candles.
* Checks for **trend reversal trade alerts** using Supertrend & 5WMA logic.
* Executes trades based on conditions and logs them accordingly.


### 📦 Setup

Clone the repository and install dependencies using:

```bash
pip install -r requirements.txt
```

Set your Zerodha credentials and PostgreSQL connection in the environment or config.



### 🧠 Strategy Summary

* Uses **Supertrend Channel** as a dynamic support/resistance range.
* Entry confirmation is done using 5-period **Weighted Moving Average (5WMA)** logic.
* Applies to both **1-minute and 5-minute timeframes**.


