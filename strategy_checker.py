"""This file handles the realtime strategy checking on the 5min alert candle and checks the trigger condition on the 1min candle fetched
    from the realtime updating POSTGRESQL database/ohlc_1min/5min. If successfull places trade based on nifty 50 index value on the 
        nearest ITM option contract based on CE/PE side trade"""

# 📌 Step 1: Import Required Libraries
import os                # For environment variables and file handling
import time              # For adding delays where needed
import datetime          # To handle timestamps
import pandas as pd      # For working with dataframes
import psycopg2          # PostgreSQL database connection
import logging           # For structured logging
from kiteconnect import KiteConnect  # Zerodha API connection

# ✅ Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.info("✅ Required libraries imported successfully.")

# ✅ Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ API Credentials
API_KEY = "xxx"  # 🔹 Replace with your actual API key
API_SECRET = "xxx"  # 🔹 Replace with your actual API secret
ACCESS_TOKEN_FILE = "access_token.txt"

# ✅ Initialize KiteConnect
kite = KiteConnect(api_key=API_KEY)

def get_access_token():
    """
    Checks if the access token exists and is valid. If not, prompts the user to manually enter a new one.
    """
    # 🔹 Step 1: Check if access_token.txt exists
    if os.path.exists(ACCESS_TOKEN_FILE):
        with open(ACCESS_TOKEN_FILE, "r") as file:
            access_token = file.read().strip()
            kite.set_access_token(access_token)
            logging.info("✅ Found existing access token. Attempting authentication...")

            # 🔹 Step 2: Validate access token
            try:
                profile = kite.profile()  # 🛠️ API call to validate token
                logging.info(f"✅ API Authentication Successful! User: {profile['user_name']}")
                return access_token  # ✅ Return the valid token
            except Exception as e:
                logging.warning(f"⚠️ Invalid/Expired Access Token: {e}")
    
    # 🔹 Step 3: If token is invalid or file does not exist, ask the user for a new one
    logging.info("🔹 Fetching new access token...")

    request_token_url = kite.login_url()
    logging.info(f"🔗 Go to this URL, authorize, and retrieve the request token: {request_token_url}")
    
    request_token = input("🔹 Paste the request token here: ").strip()

    try:
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        access_token = data["access_token"]

        # 🔹 Step 4: Save the new access token
        with open(ACCESS_TOKEN_FILE, "w") as file:
            file.write(access_token)

        logging.info("✅ New access token saved successfully!")
        return access_token
    except Exception as e:
        logging.error(f"❌ Failed to generate access token: {e}")
        return None

# ✅ Get Access Token
access_token = get_access_token()

if access_token:
    logging.info("🎯 API is now authenticated and ready to use!")
else:
    logging.error("❌ API authentication failed. Please check credentials and try again.")


import psycopg2
from psycopg2 import sql

# ✅ Database Configuration
DB_NAME = "xxx"  # 🔹 Default DB name
DB_USER = "xxx"  # 🔹 Your macOS username
DB_PASSWORD = ""  # 🔹 If no password is set, leave blank
DB_HOST = "xxx"
DB_PORT = "xxxs"  # 🔹 Default PostgreSQL port

# ✅ Connect to PostgreSQL
def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logging.info("✅ Successfully connected to PostgreSQL!")
        return conn
    except Exception as e:
        logging.error(f"❌ Failed to connect to database: {e}")
        return None


# ✅ Stores the latest 5-min OHLC data
latest_5min_data = {
    "timestamp": None,
    "5min_high": None,
    "5min_low": None,
    "5min_min_channel": None,
    "5min_max_channel": None,
    "5min_5wma": None
}

# ✅ Keeps track of active alerts
active_alert = {
    "type": None,  # "CE" or "PE"
    "timestamp": None  # Stores the timestamp when alert was triggered
}

# ✅ Stores the current trade state
trade_state = {
    "active": False,
    "entry_price": None,
    "exit_price": None,
    "trade_type": None,  # "CE" or "PE"
    "quantity": None,
    "stop_loss": None,
    "target": None
}

# ✅ Establish Database Connection
conn = connect_to_db()
cur = conn.cursor()

# ✅ Variable to Store Last Logged Time (Prevents Log Flooding)
last_logged_time = None  

import time

def get_nifty50_price():
    """
    Fetches the real-time Nifty 50 index price with retry logic.
    """
    retries = 5
    for attempt in range(retries):
        try:
            nifty_data = kite.ltp("NSE:NIFTY 50")
            nifty_price = nifty_data["NSE:NIFTY 50"]["last_price"]
            logging.info(f"✅ Fetched Nifty 50 Index Price: {nifty_price}")
            return nifty_price
        except Exception as e:
            logging.warning(f"⚠️ Attempt {attempt + 1}/{retries}: Error fetching Nifty 50 price: {e}")
            time.sleep(1)  # Wait before retrying
    
    logging.error("❌ Failed to fetch Nifty 50 price after retries.")
    return None




def get_nearest_itm_ce_contract(nifty_index_price):
    """
    Fetches the nearest ITM (In-The-Money) Call Option (CE) contract based on the Nifty 50 index price.
    """
    try:
        # ✅ Fetch all available NFO instruments
        instruments = kite.instruments("NFO")

        # ✅ Get today's date
        today = datetime.date.today()
        weekday_today = today.weekday()  # Monday = 0, Tuesday = 1, ..., Sunday = 6

        # ✅ Determine the correct weekly expiry
        if weekday_today >= 3:  # If today is Thursday or later, use next week's expiry
            expiry = today + datetime.timedelta(days=(10 - weekday_today))
        else:
            expiry = today + datetime.timedelta(days=(3 - weekday_today))

        # ✅ Format expiry components correctly
        expiry_day = f"{expiry.day:02d}"  # Ensures two-digit format (e.g., "06" instead of "6")
        expiry_month = expiry.month  # Gets numeric month (March → 3, April → 4, etc.)
        expiry_year = str(expiry.year)[-2:]  # Extracts last two digits of the year (e.g., "25" for 2025)

        # ✅ Construct the expiry identifier (e.g., "NIFTY2530622100CE" for 6th March 2025)
        expiry_identifier = f"NIFTY{expiry_year}{expiry_month}{expiry_day}"

        # ✅ Find the closest ITM CE contract
        atm_strike = round((nifty_index_price // 50) * 50) # Get the nearest strike price
        ce_symbol = f"{expiry_identifier}{atm_strike}CE"

        # ✅ Fetch the instrument token
        ce_contract = next((inst for inst in instruments if inst["tradingsymbol"] == ce_symbol), None)

        if ce_contract:
            return ce_contract["tradingsymbol"], ce_contract["instrument_token"]
        else:
            logging.warning(f"⚠️ ITM CE Contract not found for: {ce_symbol}")
            return None, None

    except Exception as e:
        logging.error(f"❌ Error fetching nearest ITM CE contract: {e}")
        return None, None



def get_nearest_itm_pe_contract(nifty_index_price):
    """
    Fetches the nearest ITM (In-The-Money) Put Option (PE) contract based on the Nifty 50 index price.
    """
    try:
        # ✅ Fetch all available NFO instruments
        instruments = kite.instruments("NFO")

        # ✅ Get today's date
        today = datetime.date.today()
        weekday_today = today.weekday()  # Monday = 0, Tuesday = 1, ..., Sunday = 6

        # ✅ Determine the correct weekly expiry
        if weekday_today >= 3:  # If today is Thursday or later, use next week's expiry
            expiry = today + datetime.timedelta(days=(10 - weekday_today))
        else:
            expiry = today + datetime.timedelta(days=(3 - weekday_today))

        # ✅ Format expiry components correctly
        expiry_day = f"{expiry.day:02d}"  # Ensures two-digit format (e.g., "06" instead of "6")
        expiry_month = expiry.month  # Gets numeric month (March → 3, April → 4, etc.)
        expiry_year = str(expiry.year)[-2:]  # Extracts last two digits of the year (e.g., "25" for 2025)

        # ✅ Construct the expiry identifier (e.g., "NIFTY2530622150PE" for 6th March 2025)
        expiry_identifier = f"NIFTY{expiry_year}{expiry_month}{expiry_day}"

        # ✅ Find the **nearest ITM PE contract** (Strike Price **Above** Current Price)
        atm_strike = round(((nifty_index_price // 50)+1) * 50)  # Get the nearest strike price
        if atm_strike < nifty_index_price:  # Ensure ITM for PE is **above** index price
            atm_strike += 50

        pe_symbol = f"{expiry_identifier}{atm_strike}PE"

        # ✅ Fetch the instrument token
        pe_contract = next((inst for inst in instruments if inst["tradingsymbol"] == pe_symbol), None)

        if pe_contract:
            return pe_contract["tradingsymbol"], pe_contract["instrument_token"]
        else:
            logging.warning(f"⚠️ ITM PE Contract not found for: {pe_symbol}")
            return None, None

    except Exception as e:
        logging.error(f"❌ Error fetching nearest ITM PE contract: {e}")
        return None, None



# Get all available option instruments
option_instruments = kite.instruments("NFO")

def get_nifty50_option_price(option_token):
    """
    Fetches the real-time price of the Nifty 50 option contract from Zerodha API.
    :param option_token: Instrument token of the Nifty 50 option contract.
    :return: Last traded price (LTP) of the option contract.
    """
    try:
        logging.info(f"🔎 Fetching LTP for token: {option_token}")
        
        # ✅ Fetch LTP from Zerodha API
        option_data = kite.ltp(option_token)

        # 📌 Log full API response to check the structure
        logging.info(f"📌 Full LTP API response: {option_data}")

        # ✅ Use token as a string directly, without "NFO:"
        token_str = str(option_token)

        if token_str in option_data:
            option_price = option_data[token_str]["last_price"]
            logging.info(f"✅ Fetched Nifty 50 Option Price: {option_price}")
            return option_price
        else:
            logging.error(f"❌ LTP response does not contain expected token: {option_token}")
            return None

    except Exception as e:
        logging.error(f"❌ Error fetching Nifty 50 option price: {e}")
        return None  # Return None if fetching fails



# 📌 WebSocket for Nifty 50 Trade Execution Monitoring
from kiteconnect import KiteTicker
import logging
import time
import os

# ✅ Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Zerodha API Credentials
API_KEY = "8re7mjcm2btaozwf"  # Replace with your API key

# ✅ Fetch access token dynamically from the file
with open("access_token.txt", "r") as f:
    ACCESS_TOKEN = f.read().strip()

# ✅ Define Instrument Token for Subscription
NIFTY_50_TOKEN = 256265  # Nifty 50 Index Token

# ✅ Initialize KiteTicker WebSocket for strategy execution
strategy_ws = KiteTicker(API_KEY, ACCESS_TOKEN)

# ✅ Store Latest Nifty 50 Price for Trade Execution Monitoring
latest_nifty_price = None

# ✅ WebSocket Event Handlers for Strategy Execution

def on_connect(ws, response):
    """Handles WebSocket connection."""
    logging.info("✅ Strategy WebSocket Connected. Subscribing to Nifty 50...")
    
    try:
        time.sleep(1)  # Small delay before subscribing
        ws.subscribe([NIFTY_50_TOKEN])
        ws.set_mode(ws.MODE_FULL, [NIFTY_50_TOKEN])  # Full mode for tick-by-tick data
        logging.info(f"📡 Subscribed to Nifty 50 (Token: {NIFTY_50_TOKEN})")
    except Exception as e:
        logging.error(f"❌ Subscription failed: {e}")

def on_ticks(ws, ticks):
    """Handles incoming tick data for trade execution monitoring."""
    global latest_nifty_price
    
    for tick in ticks:
        if tick['instrument_token'] == NIFTY_50_TOKEN:
            latest_nifty_price = tick["last_price"]
            # logging.info(f"📊 Live Nifty 50 Price: {latest_nifty_price}")
            # 🔹 Add Stop-Loss & Exit Logic Here (To Be Implemented Later)

def on_close(ws, code, reason):
    """Handles WebSocket closure and ensures reconnection."""
    logging.warning(f"⚠️ Strategy WebSocket Closed: {code}, Reason: {reason}")
    logging.info("🔄 Reconnecting in 5 seconds...")
    time.sleep(5)
    ws.connect(threaded=True, reconnect=True)

def on_error(ws, code, reason):
    """Handles WebSocket errors."""
    logging.error(f"❌ Strategy WebSocket Error! Code: {code}, Reason: {reason}")

    if "token" in reason.lower():
        logging.error("🔴 Possible access token issue! Fetch a new one and restart.")

def on_reconnect(ws, attempts):
    """Handles WebSocket reconnections."""
    logging.warning(f"🔄 Strategy WebSocket Reconnecting... Attempt {attempts}")

# ✅ Assign Event Handlers
strategy_ws.on_connect = on_connect
strategy_ws.on_ticks = on_ticks
strategy_ws.on_close = on_close
strategy_ws.on_error = on_error
strategy_ws.on_reconnect = on_reconnect

# ✅ Start WebSocket (WITHOUT Killing Other Connections)
logging.info("🚀 Starting Strategy WebSocket...")
strategy_ws.connect(threaded=True)


# ✅ Infinite Loop to Continuously Check for New 5-Minute Data
while True:
    # logging.info("🔄 Still checking for alerts & triggers...")
    # ✅ Step 1: Get the current time's minute value
    now = datetime.datetime.now()
    curtime = now.minute  # Extracting the minute value

    # ✅ Step 2: Compute reqd_time as the largest multiple of 5 that is **LESS THAN** curtime
    if curtime % 5 == 0:  
        reqd_time = (curtime - 5) % 60  # If curtime is a multiple of 5, take the previous multiple
    else:
        reqd_time = (curtime // 5) * 5  # Otherwise, take the largest multiple of 5 below curtime

    # ✅ Step 3: Fetch the last row from ohlc_5min
    cur.execute("SELECT timestamp FROM ohlc_5min ORDER BY timestamp DESC LIMIT 1;")
    last_row = cur.fetchone()

    if last_row:
        last_timestamp = last_row[0]
        fetched_time = last_timestamp.minute  # Extract the minute value from the timestamp
    else:
        if last_logged_time != curtime:  # Prevent repeated logs in the same minute
            
            last_logged_time = curtime  # Update logged time
        time.sleep(1)
        continue  # Skip this iteration and retry

    # ✅ Step 4: Compare fetched_time with reqd_time
    if fetched_time != reqd_time:
        if last_logged_time != curtime:  # Log only once per minute
            
            last_logged_time = curtime  # Update last logged time
        time.sleep(1)
        continue  # Skip this iteration and retry

    # ✅ Step 5: If new data is available, start checking for possible ce and pe trades 
    if last_logged_time != reqd_time:  # Log only when a new candle appears
        last_logged_time = reqd_time  # Update last logged time to prevent flooding
        time.sleep(10)
        while True:
            
            cur.execute("""
                SELECT timestamp, high, low, min_channel, max_channel, five_wma
                FROM ohlc_5min 
                WHERE min_channel IS NOT NULL AND max_channel IS NOT NULL AND five_wma IS NOT NULL
                ORDER BY timestamp DESC 
                LIMIT 1;
                """)
            row = cur.fetchone()

            if row:  # ✅ If min_channel and max_channel are available, break the loop
                break
            else:
                time.sleep(0.5)  # 🔄 Wait and try again

            # ✅ Now that Min & Max Channels are available, wait 1 second before fetching 5WMA
        time.sleep(1.5)

        # ✅ Fetch complete data including 5WMA
        cur.execute("""
            SELECT timestamp, high, low, min_channel, max_channel, five_wma 
            FROM ohlc_5min 
            ORDER BY timestamp DESC 
            LIMIT 1;
            """)
        row = cur.fetchone()

        if row:
            latest_5min_data["timestamp"] = row[0]
            latest_5min_data["5min_high"] = row[1]
            latest_5min_data["5min_low"] = row[2]
            latest_5min_data["5min_min_channel"] = row[3]
            latest_5min_data["5min_max_channel"] = row[4]
            latest_5min_data["5min_5wma"] = row[5]

            logging.info(f"✅ Stored Latest 5-Min Data: {latest_5min_data}")


        # ✅ Check CE Condition
        ce_alert = False  # Default to False

        # Ensure data is available before checking conditions
        if all([
            latest_5min_data["5min_high"] is not None,
            latest_5min_data["5min_low"] is not None,
            latest_5min_data["5min_min_channel"] is not None,
            latest_5min_data["5min_5wma"] is not None
        ]):
            # Condition 1: 5min high >= 5min min channel
            if latest_5min_data["5min_high"] >= latest_5min_data["5min_min_channel"]:
                # Condition 2: 5min low <= 5min min channel
                if latest_5min_data["5min_low"] <= latest_5min_data["5min_min_channel"]:
                    # Condition 3: 5min 5WMA > 5min high -> gap condition 
                    if latest_5min_data["5min_5wma"] > latest_5min_data["5min_high"]:
                        ce_alert = True  # ✅ CE alert is satisfied

            # if latest_5min_data["5min_high"] > latest_5min_data["5min_low"]:
            #     ce_alert = True  # ✅ CE alert is satisfied


        # ✅ Initialize CE Trigger Variable
        ce_trigger = False

        # ✅ If CE Alert was triggered, start checking for the next 7 new candles
        if ce_alert:
            logging.info("🚀 CE Alert Condition Satisfied! Monitoring next 7 new candles for trigger...")

            # ✅ Fetch the latest 1-minute candle before starting the loop
            cur.execute("""
                SELECT timestamp, close, rolling_5wma 
                FROM ohlc_1min 
                ORDER BY timestamp DESC 
                LIMIT 1;
            """)
            row = cur.fetchone()

            if row:
                latest_1min_candle = {
                    "timestamp": row[0],
                    "close": row[1],
                    "rolling_5wma": row[2]
                }
            else:
                logging.error("❌ No 1-minute data available. Cannot check CE trigger.")
                latest_1min_candle = None

            # ✅ Start monitoring loop
            counter = 1  # We need exactly 7 new candles
            while counter <= 7:
                time.sleep(1)  # 🔄 Check every second
        
                fetch_attempts = 0  # ✅ Reset fetch attempt counter for each new candle fetch
                while fetch_attempts < 3:  # ✅ Retry up to 3 times if data contains None values
                    # ✅ Fetch the latest 1-minute candle
                    cur.execute("""
                        SELECT timestamp, close, rolling_5wma 
                        FROM ohlc_1min 
                        ORDER BY timestamp DESC 
                        LIMIT 1;
                    """)
                    row = cur.fetchone()

                    if row:
                        new_timestamp, new_close, new_rolling_5wma = row

                        # ✅ If fetched data contains None, retry fetching
                        if new_close is None or new_rolling_5wma is None:
                            logging.warning("⚠️ Fetched 1-min data contains None values. Retrying...")
                            time.sleep(1)
                            fetch_attempts += 1
                        else:
                            break  # ✅ Exit retry loop once valid data is fetched

                # ✅ If we have a **new** 1-minute candle
                if new_timestamp != latest_1min_candle["timestamp"]:
                    latest_1min_candle = {
                        "timestamp": new_timestamp,
                        "close": new_close,
                        "rolling_5wma": new_rolling_5wma
                    }

                    counter += 1  # ✅ Only increment counter when a new candle appears

                    # ✅ Check CE Trigger Condition
                    if new_close > latest_5min_data["5min_high"] and new_rolling_5wma > latest_5min_data["5min_high"]:
                    # if new_close == new_close: #sample check to test the working of ce execution 
                        ce_trigger = True
                        logging.info(f"🚀 CE Trigger Successful at {new_timestamp}! Trade execution can proceed.")
                        
                        ### Trade execution logic for CE will go here ###
                        import time

                        # ✅ Fetch Nifty 50 Index Price (Entry Price)
                        nifty_entry_price = get_nifty50_price()

                        if nifty_entry_price is not None:
                            logging.info(f"📊 Using Nifty 50 Index Price as Entry Price: {nifty_entry_price}")

                            # ✅ Fetch Nearest ITM CE Contract
                            ce_contract_symbol, ce_instrument_token = get_nearest_itm_ce_contract(nifty_entry_price)

                            if ce_contract_symbol and ce_instrument_token:
                                logging.info(f"📈 Using CE Contract: {ce_contract_symbol} (Token: {ce_instrument_token}) for trade execution")

                                # ✅ Place Buy Order for CE Contract (Market Order)
                                try:
                                    order_id = kite.place_order(
                                        variety=kite.VARIETY_REGULAR,
                                        exchange=kite.EXCHANGE_NFO,
                                        tradingsymbol=ce_contract_symbol,
                                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                                        quantity=75,  # Adjust quantity as needed
                                        order_type=kite.ORDER_TYPE_MARKET,  # 📌 Market Order
                                        product=kite.PRODUCT_MIS  
                                    )
                                    logging.info(f"✅ CE Buy Order Placed Successfully! Order ID: {order_id}")

                                    # ✅ Set Initial Stop Loss (SL) from the 5-min Alert Candle
                                    stop_loss = latest_5min_data["5min_min_channel"]
                                    logging.info(f"🔻 Initial Stop Loss Set: {stop_loss}")

                                    # ✅ Define Target Levels (Based on Nifty 50 Index Price)
                                    target_1 = nifty_entry_price + 30
                                    target_2 = nifty_entry_price + 55
                                    target_3 = nifty_entry_price + 105

                                    # ✅ Trailing Stop-Loss Levels
                                    sl_update_1 = nifty_entry_price + 25
                                    sl_update_2 = nifty_entry_price + 50
                                    sl_update_3 = nifty_entry_price + 100

                                    logging.info(f"🎯 Targets: {target_1}, {target_2}, {target_3}")
                                    logging.info(f"🔄 Trailing SL Updates: {sl_update_1}, {sl_update_2}, {sl_update_3}")

                                    trade_active = True

                                    # ✅ Monitor Nifty 50 Tick Data for SL & Target Conditions
                                    while trade_active:
                                        time.sleep(1)  # Small delay to avoid excessive CPU usage

                                        # ✅ Fetch latest Nifty 50 LTP (from WebSocket)
                                        latest_nifty_ltp = latest_nifty_price  # Using live tick data from WebSocket

                                        if latest_nifty_ltp is not None:
                                            logging.info(f"📡 Live Nifty 50 LTP: {latest_nifty_ltp}")

                                            # ✅ Exit if SL is hit
                                            if latest_nifty_ltp <= stop_loss:
                                                logging.info(f"🚨 Stop Loss Hit! Exiting trade at CMP ({latest_nifty_ltp})")
                                                kite.place_order(
                                                    variety=kite.VARIETY_REGULAR,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    tradingsymbol=ce_contract_symbol,
                                                    transaction_type=kite.TRANSACTION_TYPE_SELL,
                                                    quantity=75,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    product=kite.PRODUCT_MIS
                                                )
                                                trade_active = False
                                                logging.info(f"❌ CE Trade Exited at {latest_nifty_ltp} due to SL Hit.")
                                                break

                                            # ✅ Target 1 Hit → Update SL
                                            if latest_nifty_ltp >= target_1 and stop_loss == latest_5min_data["5min_min_channel"]:
                                                stop_loss = sl_update_1
                                                logging.info(f"🎯 Target 1 Hit! New SL: {stop_loss}")

                                            # ✅ Target 2 Hit → Update SL
                                            if latest_nifty_ltp >= target_2 and stop_loss == sl_update_1:
                                                stop_loss = sl_update_2
                                                logging.info(f"🎯 Target 2 Hit! New SL: {stop_loss}")

                                            # ✅ Target 3 Hit → Exit Trade at CMP
                                            if latest_nifty_ltp >= target_3:
                                                logging.info(f"🎯 Final Target Hit! Exiting trade at CMP ({latest_nifty_ltp})")
                                                kite.place_order(
                                                    variety=kite.VARIETY_REGULAR,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    tradingsymbol=ce_contract_symbol,
                                                    transaction_type=kite.TRANSACTION_TYPE_SELL,
                                                    quantity=75,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    product=kite.PRODUCT_MIS
                                                )
                                                trade_active = False
                                                logging.info(f"✅ CE Trade Exited at {latest_nifty_ltp} due to Target 3 Hit.")
                                                break

                                except Exception as e:
                                    logging.error(f"❌ CE Buy Order Failed: {e}")

                            else:
                                logging.error("❌ Failed to fetch CE contract. Skipping trade execution.")

                        else:
                            logging.error("❌ Failed to fetch Nifty 50 Index Price. Cannot execute trade.")

                        break     #Stop checking further for trades 
                    else:
                        logging.info(f"❌ CE Trigger Failed at {new_timestamp}! Checking next candle...")
            if not ce_trigger:
                logging.info("❌ CE Trigger Failed! No valid trigger found in 7 new candles.")
        else:
            logging.info("❌ CE Alert Condition NOT Satisfied. Moving to checking PE.")

        # ✅ Check PE Condition
        pe_alert = False  # Default to False

        # Ensure data is available before checking conditions
        if all([
            latest_5min_data["5min_high"] is not None,
            latest_5min_data["5min_low"] is not None,
            latest_5min_data["5min_max_channel"] is not None,
            latest_5min_data["5min_5wma"] is not None
        ]):
            # Condition 1: 5min high >= 5min max channel
            if latest_5min_data["5min_high"] >= latest_5min_data["5min_max_channel"]:
                # Condition 2: 5min low <= 5min max channel
                if latest_5min_data["5min_low"] <= latest_5min_data["5min_max_channel"]:
                    # Condition 3: 5min 5WMA < 5min low -> gap condition 
                    if latest_5min_data["5min_5wma"] < latest_5min_data["5min_low"]:
                        pe_alert = True  # ✅ PE alert is satisfied

        # ✅ Initialize PE Trigger Variable
        pe_trigger = False

        # ✅ If PE Alert was triggered, start checking for the next 7 new candles
        if pe_alert:
            logging.info("🚀 PE Alert Condition Satisfied! Monitoring next 7 new candles for trigger...")

            # ✅ Fetch the latest 1-minute candle before starting the loop
            cur.execute("""
                SELECT timestamp, close, rolling_5wma 
                FROM ohlc_1min 
                ORDER BY timestamp DESC 
                LIMIT 1;
            """)
            row = cur.fetchone()

            if row:
                latest_1min_candle = {
                    "timestamp": row[0],
                    "close": row[1],
                    "rolling_5wma": row[2]
                }
            else:
                logging.error("❌ No 1-minute data available. Cannot check PE trigger.")
                latest_1min_candle = None

            # ✅ Start monitoring loop
            counter = 1  # We need exactly 7 new candles
            while counter <= 7:
                time.sleep(1)  # 🔄 Check every second

                # ✅ Fetch the latest 1-minute candle
                fetch_attempts = 0
                new_timestamp, new_close, new_rolling_5wma = None, None, None

                while fetch_attempts < 3:  # Retry up to 3 times if values are None
                    cur.execute("""
                        SELECT timestamp, close, rolling_5wma 
                        FROM ohlc_1min 
                        ORDER BY timestamp DESC 
                        LIMIT 1;
                    """)
                    row = cur.fetchone()

                    if row:
                        new_timestamp, new_close, new_rolling_5wma = row
            
                    # ✅ If any fetched value is None, wait and retry
                    if new_close is None or new_rolling_5wma is None:
                        logging.warning("⚠️ Fetched 1-min data contains None values. Retrying in 1 second...")
                        time.sleep(1)
                        fetch_attempts += 1
                    else:
                        break  # ✅ Break loop once valid data is fetched

                # ✅ If we have a **new** 1-minute candle
                if new_timestamp != latest_1min_candle["timestamp"]:
                    latest_1min_candle = {
                        "timestamp": new_timestamp,
                        "close": new_close,
                        "rolling_5wma": new_rolling_5wma
                    }

                    counter += 1  # ✅ Only increment counter when a new candle appears

                    # ✅ Check PE Trigger Condition
                    if new_close < latest_5min_data["5min_low"] and new_rolling_5wma < latest_5min_data["5min_low"]:
                        pe_trigger = True
                        logging.info(f"🚀 PE Trigger Successful at {new_timestamp}! Trade execution can proceed.")

                        #Trade execution logic for PE 
                        import time

                        # ✅ Fetch Nifty 50 Index Price (Entry Price)
                        nifty_entry_price = get_nifty50_price()

                        if nifty_entry_price is not None:
                            logging.info(f"📊 Using Nifty 50 Index Price as Entry Price: {nifty_entry_price}")

                            # ✅ Fetch Nearest ITM PE Contract
                            pe_contract_symbol, pe_instrument_token = get_nearest_itm_pe_contract(nifty_entry_price)

                            if pe_contract_symbol and pe_instrument_token:
                                logging.info(f"📈 Using PE Contract: {pe_contract_symbol} (Token: {pe_instrument_token}) for trade execution")

                                # ✅ Place Buy Order for PE Contract (Market Order)
                                try:
                                    order_id = kite.place_order(
                                        variety=kite.VARIETY_REGULAR,
                                        exchange=kite.EXCHANGE_NFO,
                                        tradingsymbol=pe_contract_symbol,
                                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                                        quantity=75,  # Adjust quantity as needed
                                        order_type=kite.ORDER_TYPE_MARKET,  # 📌 Market Order
                                        product=kite.PRODUCT_MIS  
                                    )
                                    logging.info(f"✅ PE Buy Order Placed Successfully! Order ID: {order_id}")

                                    # ✅ Set Initial Stop Loss (SL) from the 5-min Alert Candle
                                    stop_loss = latest_5min_data["5min_max_channel"]
                                    logging.info(f"🔻 Initial Stop Loss Set: {stop_loss}")

                                    # ✅ Define Target Levels (Based on Nifty 50 Index Price)
                                    target_1 = nifty_entry_price - 30
                                    target_2 = nifty_entry_price - 55
                                    target_3 = nifty_entry_price - 105

                                    # ✅ Trailing Stop-Loss Levels
                                    sl_update_1 = nifty_entry_price - 25
                                    sl_update_2 = nifty_entry_price - 50
                                    sl_update_3 = nifty_entry_price - 100

                                    logging.info(f"🎯 Targets: {target_1}, {target_2}, {target_3}")
                                    logging.info(f"🔄 Trailing SL Updates: {sl_update_1}, {sl_update_2}, {sl_update_3}")

                                    trade_active = True

                                    # ✅ Monitor Nifty 50 Tick Data for SL & Target Conditions
                                    while trade_active:
                                        time.sleep(1)  # Small delay to avoid excessive CPU usage

                                        # ✅ Fetch latest Nifty 50 LTP (from WebSocket)
                                        latest_nifty_ltp = latest_nifty_price  # Using live tick data from WebSocket

                                        if latest_nifty_ltp is not None:
                                            logging.info(f"📡 Live Nifty 50 LTP: {latest_nifty_ltp}")

                                            # ✅ Exit if SL is hit
                                            if latest_nifty_ltp >= stop_loss:
                                                logging.info(f"🚨 Stop Loss Hit! Exiting trade at CMP ({latest_nifty_ltp})")
                                                kite.place_order(
                                                    variety=kite.VARIETY_REGULAR,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    tradingsymbol=pe_contract_symbol,
                                                    transaction_type=kite.TRANSACTION_TYPE_SELL,
                                                    quantity=75,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    product=kite.PRODUCT_MIS
                                                )
                                                trade_active = False
                                                logging.info(f"❌ PE Trade Exited at {latest_nifty_ltp} due to SL Hit.")
                                                break

                                            # ✅ Target 1 Hit → Update SL
                                            if latest_nifty_ltp <= target_1 and stop_loss == latest_5min_data["5min_max_channel"]:
                                                stop_loss = sl_update_1
                                                logging.info(f"🎯 Target 1 Hit! New SL: {stop_loss}")

                                            # ✅ Target 2 Hit → Update SL
                                            if latest_nifty_ltp <= target_2 and stop_loss == sl_update_1:
                                                stop_loss = sl_update_2
                                                logging.info(f"🎯 Target 2 Hit! New SL: {stop_loss}")

                                            # ✅ Target 3 Hit → Exit Trade at CMP
                                            if latest_nifty_ltp <= target_3:
                                                logging.info(f"🎯 Final Target Hit! Exiting trade at CMP ({latest_nifty_ltp})")
                                                kite.place_order(
                                                    variety=kite.VARIETY_REGULAR,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    tradingsymbol=pe_contract_symbol,
                                                    transaction_type=kite.TRANSACTION_TYPE_SELL,
                                                    quantity=75,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    product=kite.PRODUCT_MIS
                                                )
                                                trade_active = False
                                                logging.info(f"✅ PE Trade Exited at {latest_nifty_ltp} due to Target 3 Hit.")
                                                break

                                except Exception as e:
                                    logging.error(f"❌ PE Buy Order Failed: {e}")

                            else:
                                logging.error("❌ Failed to fetch PE contract. Skipping trade execution.")

                        else:
                            logging.error("❌ Failed to fetch Nifty 50 Index Price. Cannot execute trade.")

                        break     #Stop checking further for trades 

                    else:
                        logging.info(f"❌ PE Trigger Failed at {new_timestamp}! Checking trigger execution on new candle...")
            if not pe_trigger:
                logging.info("❌ PE Trigger Failed! No valid trigger found in 7 new candles.")
        else:
            logging.info("❌ PE Alert Condition NOT Satisfied. Moving to next cycle.")


    # 🔹 TODO: Next Steps - Alert Condition, Trigger Condition, Executing Trades

    time.sleep(1)  # Small delay to avoid excessive CPU usage

    

