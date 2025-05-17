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
DB_PORT = "xxx"  # 🔹 Default PostgreSQL port

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

# ✅ Create OHLC Tables and Clear Existing Data
def create_ohlc_tables():
    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()

            # 🔹 DROP TABLES FIRST to remove old schema
            cur.execute("DROP TABLE IF EXISTS ohlc_1min CASCADE;")
            cur.execute("DROP TABLE IF EXISTS ohlc_5min CASCADE;")
            logging.info("✅ Dropped existing OHLC tables to apply schema changes.")

            # 🔹 Create New Tables
            create_table_queries = [
                """
                CREATE TABLE ohlc_1min (
                    timestamp TIMESTAMPTZ PRIMARY KEY,
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    rolling_5wma FLOAT
                );
                """,
                """
                CREATE TABLE ohlc_5min (
                    timestamp TIMESTAMPTZ PRIMARY KEY,
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    hl2 FLOAT,
                    atr FLOAT,
                    initial_upper_bar FLOAT,
                    initial_lower_bar FLOAT,
                    supertrend_upper FLOAT,
                    supertrend_lower FLOAT,
                    os FLOAT,
                    spt FLOAT,
                    max_channel FLOAT,
                    min_channel FLOAT,
                    supertrend_avg FLOAT,
                    five_wma FLOAT
                );
                """
            ]

            # 🔹 Execute Queries
            for query in create_table_queries:
                cur.execute(query)

            conn.commit()
            logging.info("✅ Tables 'ohlc_1min' and 'ohlc_5min' are successfully created with correct schema!")

            cur.close()
            conn.close()
        except Exception as e:
            logging.error(f"❌ Failed to create/update tables: {e}")

# ✅ Initialize Database & Tables
create_ohlc_tables()

# ✅ Market Holidays for 2025
MARKET_HOLIDAYS = {
    "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-10",
    "2025-04-14", "2025-04-18", "2025-05-01", "2025-08-15",
    "2025-08-27", "2025-10-02", "2025-10-21", "2025-10-22",
    "2025-11-05", "2025-12-25"
}
import pandas as pd


# ✅ Function to Fetch Instrument Token for CRUDEOIL MAR FUT
def get_natgas_march_token():
    try:
        # 🔹 Fetch all instruments list
        instruments = kite.instruments("MCX")  # Get only MCX instruments

        # 🔹 Filter the required contract
        for instrument in instruments:
            if instrument["tradingsymbol"].startswith("NATURALGAS") and "MAR" in instrument["tradingsymbol"]:
                logging.info(f"✅ Found NATURALGAS MAR FUT Token: {instrument['instrument_token']}")
                return instrument["instrument_token"]
        
        logging.warning("⚠️ NATURALGAS MAR FUT contract not found!")
        return None

    except Exception as e:
        logging.error(f"❌ Error fetching instrument token: {e}")
        return None

# ✅ Fetch and Print the Instrument Token
natgas_token = get_natgas_march_token()
print(f"NATURALGAS MARCH FUT Instrument Token: {natgas_token}")
# #Fetch the instrument token for Silver Feb futures
# def get_instrument_token(trading_symbol, exchange="MCX"):
#     """
#     Fetches the instrument token for a given trading symbol from the Kite API.
    
#     :param trading_symbol: The symbol of the instrument (e.g., "SILVERM25FEBFUT").
#     :param exchange: The exchange (default is "MCX").
#     :return: The instrument token if found, else None.
#     """
#     try:
#         # Fetch all instruments from the specified exchange
#         instruments = kite.instruments(exchange)
        
#         # Convert to DataFrame
#         df = pd.DataFrame(instruments)

#         # Filter for the specific trading symbol
#         instrument_row = df[df["tradingsymbol"] == trading_symbol]

#         if not instrument_row.empty:
#             instrument_token = instrument_row["instrument_token"].values[0]
#             print(f"✅ Instrument Token for {trading_symbol}: {instrument_token}")
#             return instrument_token
#         else:
#             print(f"❌ Instrument Token not found for {trading_symbol}.")
#             return None

#     except Exception as e:
#         print(f"❌ Error fetching instrument token: {e}")
#         return None

# # Example usage: Fetching token for "SILVERM25FEBFUT"
# silverm_feb_token = get_instrument_token("SILVERM25FEBFUT", "MCX")

# ✅ Fetch Last Trading Day's Data
def fetch_last_trading_day_ohlc(interval):
    """Fetches and stores last trading day's OHLC data in PostgreSQL."""
    try:
        conn = connect_to_db()
        if not conn:
            return None

        now = datetime.datetime.now()
        last_trading_day = now - datetime.timedelta(days=1)

        while last_trading_day.strftime("%Y-%m-%d") in MARKET_HOLIDAYS or last_trading_day.weekday() in [5, 6]:
            last_trading_day -= datetime.timedelta(days=1)

        from_date = last_trading_day.strftime("%Y-%m-%d 09:15:00") 
        to_date = last_trading_day.strftime("%Y-%m-%d 15:30:00")

        # from_date = last_trading_day.strftime("%Y-%m-%d 09:00:00") #Timings for silver feb futures
        # to_date = last_trading_day.strftime("%Y-%m-%d 23:55:00")

        logging.info(f"📅 Fetching last trading day's {interval} data: {from_date} to {to_date}")

        historical_data = kite.historical_data(
            instrument_token=256265,
            from_date=from_date,                  #nifty 50 
            to_date=to_date,
            interval=interval
        )

        # historical_data = kite.historical_data(
        #     instrument_token=112703495,
        #     from_date=from_date,                #instrument token for natgas march futures
        #     to_date=to_date,
        #     interval=interval
        # )

        

        df = pd.DataFrame(historical_data)
        if df.empty:
            logging.warning(f"⚠️ No {interval} data fetched for the last trading day.")
            return None

        df["timestamp"] = pd.to_datetime(df["date"])
        df.drop(columns=["date"], inplace=True)

        # 🔹 Store Data in PostgreSQL
        table_name = "ohlc_1min" if interval == "minute" else "ohlc_5min"
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute(f"""
                    INSERT INTO {table_name} (timestamp, open, high, low, close)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp) DO NOTHING;
                """, (row["timestamp"], row["open"], row["high"], row["low"], row["close"]))

        conn.commit()
        logging.info(f"✅ Last trading day's {interval} data stored in PostgreSQL.")
        conn.close()
        return df
    except Exception as e:
        logging.error(f"❌ Error fetching last trading day's {interval} data: {e}")
        return None

# ✅ Fetch & Merge Today's Data
def fetch_and_merge_ohlc(interval):
    """Fetches today's OHLC data and merges it with last trading day's OHLC data in PostgreSQL."""
    conn = connect_to_db()
    if not conn:
        return

    df_last_trading_day = fetch_last_trading_day_ohlc(interval)
    if df_last_trading_day is None:
        logging.warning(f"⚠️ No last trading day data available for {interval}. Skipping merge.")
        return

    now = datetime.datetime.now()
    from_date = now.replace(hour=9, minute=15, second=0).strftime("%Y-%m-%d %H:%M:%S")
    
    # 🔹 To exclude the currently forming candle:
    if interval == "minute":
        to_date = (now - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    else:  # For 5-minute interval
        to_date = now.replace(minute=(now.minute // 5) * 5, second=0).strftime("%Y-%m-%d %H:%M:%S")

    logging.info(f"📅 Fetching today's {interval} data from: {from_date} to {to_date}")

    historical_data = kite.historical_data(
        instrument_token=256265,
        from_date=from_date,
        to_date=to_date,
        interval=interval
    )

    # historical_data = kite.historical_data(
    #     instrument_token=112703495,         #instrument token for nat gas march futures
    #     from_date=from_date,
    #     to_date=to_date,
    #     interval=interval
    # )



    df_today = pd.DataFrame(historical_data)
    if df_today.empty:
        logging.warning(f"⚠️ No live {interval} data available yet.")
        return

    df_today["timestamp"] = pd.to_datetime(df_today["date"])
    df_today.drop(columns=["date"], inplace=True)

    # 🔹 Store Today's Data in PostgreSQL
    table_name = "ohlc_1min" if interval == "minute" else "ohlc_5min"
    with conn.cursor() as cur:
        for _, row in df_today.iterrows():
            cur.execute(f"""
                INSERT INTO {table_name} (timestamp, open, high, low, close)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (timestamp) DO NOTHING;
            """, (row["timestamp"], row["open"], row["high"], row["low"], row["close"]))

    conn.commit()
    logging.info(f"✅ Merged live data with last trading day's data for {interval} and stored in PostgreSQL.")
    conn.close()

# ✅ Fetch & Merge Data for Both 1min & 5min OHLC
fetch_and_merge_ohlc("minute")
fetch_and_merge_ohlc("5minute")

logging.info("✅ OHLC data fetching & storing completed for both 1-minute and 5-minute data!")

# historical_data = kite.historical_data(
    #     instrument_token=112703495,         #instrument token for nat gas march futures
    #     from_date=from_date,
    #     to_date=to_date,
    #     interval=interval
    # )

def calculate_hl2():
    """
    Calculate HL2 (High-Low Midpoint) and update it in the PostgreSQL database for ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Update HL2 column in ohlc_5min table
        update_query = """
        UPDATE ohlc_5min 
        SET hl2 = (high + low) / 2;
        """

        cur.execute(update_query)
        conn.commit()

        logging.info("✅ HL2 column calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating HL2: {e}")

# ✅ Run the function to calculate & update HL2
calculate_hl2()

# ✅ ATR SETTINGS
ATR_LENGTH = 10
ATR_MULTIPLIER = 3

def calculate_atr():
    """
    Calculate ATR (Average True Range) using RMA (Wilder's Moving Average)
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, high, low, close FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for ATR calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize columns for True Range and ATR
        df['true_range'] = 0.0
        df['atr'] = 0.0

        # ✅ Calculate True Range (TR) - Exact Colab Logic
        for i in range(1, len(df)):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            prev_close = df.iloc[i - 1]['close']

            tr = max(
                high - low,  # High - Low
                abs(high - prev_close),  # High - Previous Close
                abs(low - prev_close)  # Low - Previous Close
            )
            df.at[df.index[i], 'true_range'] = tr

        # ✅ Calculate ATR using Wilder’s RMA (Colab Logic)
        for i in range(len(df)):
            if i == 0:
                df.at[df.index[i], 'atr'] = 0.0
            elif i < ATR_LENGTH:
                df.at[df.index[i], 'atr'] = df['true_range'][:i+1].mean()
            else:
                prev_atr = df.iloc[i - 1]['atr']
                tr = df.iloc[i]['true_range']
                df.at[df.index[i], 'atr'] = ((prev_atr * (ATR_LENGTH - 1)) + tr) / ATR_LENGTH

        # ✅ Apply ATR Multiplier (Only If Needed)
        df['atr'] *= ATR_MULTIPLIER

        # ✅ Drop the intermediate 'true_range' column
        df.drop(columns=['true_range'], inplace=True)

        # ✅ Convert timestamp & ATR values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['atr'] = df['atr'].astype(float)  # Ensure proper float values

        # ✅ Update ATR values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET atr = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['atr'], row['timestamp']))

        conn.commit()
        logging.info("✅ ATR (RMA-based) calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating ATR: {e}")

# ✅ Run the function to calculate & update ATR
calculate_atr()




def calculate_initial_upper_band():
    """
    Calculate the Initial Upper Band and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure HL2 and ATR exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='hl2');")
        hl2_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='atr');")
        atr_exists = cur.fetchone()[0]

        if not hl2_exists or not atr_exists:
            logging.error("❌ Required columns 'hl2' or 'atr' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Update Initial Upper Band in PostgreSQL
        update_query = """
        UPDATE ohlc_5min 
        SET initial_upper_bar = hl2 + atr;
        """
        cur.execute(update_query)

        conn.commit()
        logging.info("✅ Initial Upper Band calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Initial Upper Band: {e}")

# ✅ Run the function to calculate & update Initial Upper Band
calculate_initial_upper_band()



def calculate_initial_lower_band():
    """
    Calculate the Initial Lower Band and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure HL2 and ATR exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='hl2');")
        hl2_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='atr');")
        atr_exists = cur.fetchone()[0]

        if not hl2_exists or not atr_exists:
            logging.error("❌ Required columns 'hl2' or 'atr' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Update Initial Lower Band in PostgreSQL
        update_query = """
        UPDATE ohlc_5min 
        SET initial_lower_bar = hl2 - atr;
        """
        cur.execute(update_query)

        conn.commit()
        logging.info("✅ Initial Lower Band calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Initial Lower Band: {e}")

# ✅ Run the function to calculate & update Initial Lower Band
calculate_initial_lower_band()



def calculate_supertrend_upper():
    """
    Calculate the Dynamic Supertrend Upper Band using the previous close
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='initial_upper_bar');")
        initial_upper_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='close');")
        close_exists = cur.fetchone()[0]

        if not initial_upper_exists or not close_exists:
            logging.error("❌ Required columns 'initial_upper_bar' or 'close' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, initial_upper_bar, close FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Supertrend Upper calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'initial_upper_bar', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize the Supertrend Upper Band column
        df['supertrend_upper'] = 0.0

        # ✅ Calculate Dynamic Supertrend Upper Band
        for i in range(len(df)):
            if i == 0:
                # First row: Set the Supertrend Upper Band to the Initial Upper Band
                df.at[i, 'supertrend_upper'] = df.at[i, 'initial_upper_bar']
            else:
                prev_supertrend_upper = df.at[i - 1, 'supertrend_upper']
                initial_upper = df.at[i, 'initial_upper_bar']
                prev_close = df.at[i - 1, 'close']

                # Apply dynamic adjustment logic
                if prev_close < prev_supertrend_upper:
                    df.at[i, 'supertrend_upper'] = min(initial_upper, prev_supertrend_upper)
                else:
                    df.at[i, 'supertrend_upper'] = initial_upper

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['supertrend_upper'] = df['supertrend_upper'].astype(float)  # Ensure proper float values

        # ✅ Update Supertrend Upper Band values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET supertrend_upper = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['supertrend_upper'], row['timestamp']))

        conn.commit()
        logging.info("✅ Supertrend Upper Band calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Supertrend Upper Band: {e}")

# ✅ Run the function to calculate & update Supertrend Upper Band
calculate_supertrend_upper()



def calculate_supertrend_lower():
    """
    Calculate the Dynamic Supertrend Lower Band using the previous close
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='initial_lower_bar');")
        initial_lower_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='close');")
        close_exists = cur.fetchone()[0]

        if not initial_lower_exists or not close_exists:
            logging.error("❌ Required columns 'initial_lower_bar' or 'close' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, initial_lower_bar, close FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Supertrend Lower calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'initial_lower_bar', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize the Supertrend Lower Band column
        df['supertrend_lower'] = 0.0

        # ✅ Calculate Dynamic Supertrend Lower Band
        for i in range(len(df)):
            if i == 0:
                # First row: Set the Supertrend Lower Band to the Initial Lower Band
                df.at[i, 'supertrend_lower'] = df.at[i, 'initial_lower_bar']
            else:
                prev_supertrend_lower = df.at[i - 1, 'supertrend_lower']
                initial_lower = df.at[i, 'initial_lower_bar']
                prev_close = df.at[i - 1, 'close']

                # Apply dynamic adjustment logic
                if prev_close >= prev_supertrend_lower:
                    df.at[i, 'supertrend_lower'] = max(initial_lower, prev_supertrend_lower)
                else:
                    df.at[i, 'supertrend_lower'] = initial_lower

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['supertrend_lower'] = df['supertrend_lower'].astype(float)  # Ensure proper float values

        # ✅ Update Supertrend Lower Band values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET supertrend_lower = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['supertrend_lower'], row['timestamp']))

        conn.commit()
        logging.info("✅ Supertrend Lower Band calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Supertrend Lower Band: {e}")

# ✅ Run the function to calculate & update Supertrend Lower Band
calculate_supertrend_lower()



import psycopg2
import logging

def calculate_oscillation_state():
    """
    Calculate the Oscillation State (os) using current row data
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='supertrend_upper');")
        supertrend_upper_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='supertrend_lower');")
        supertrend_lower_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='close');")
        close_exists = cur.fetchone()[0]

        if not (supertrend_upper_exists and supertrend_lower_exists and close_exists):
            logging.error("❌ Required columns 'supertrend_upper', 'supertrend_lower', or 'close' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, close, supertrend_upper, supertrend_lower FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Oscillation State calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'close', 'supertrend_upper', 'supertrend_lower'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize the Oscillation State column
        df['os'] = 0  # Default to bearish

        # ✅ Calculate the Oscillation State
        for i in range(len(df)):
            close = df.at[i, 'close']
            upper_band = df.at[i, 'supertrend_upper']
            lower_band = df.at[i, 'supertrend_lower']

            # Compare the current close with the current bands
            if close > upper_band:
                df.at[i, 'os'] = 1  # Bullish
            elif close < lower_band:
                df.at[i, 'os'] = 0  # Bearish
            else:
                if i > 0:
                    # Retain the previous state if close is between the bands
                    df.at[i, 'os'] = df.at[i - 1, 'os']
                else:
                    # For the first row, default to bearish if between bands
                    df.at[i, 'os'] = 0

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['os'] = df['os'].astype(int)  # Ensure proper integer values

        # ✅ Update Oscillation State values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET os = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['os'], row['timestamp']))

        conn.commit()
        logging.info("✅ Oscillation State (os) calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Oscillation State: {e}")

# ✅ Run the function to calculate & update Oscillation State
calculate_oscillation_state()


def calculate_supertrend_pivot():
    """
    Calculate the Supertrend Pivot (spt) and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='os');")
        os_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='supertrend_upper');")
        supertrend_upper_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='supertrend_lower');")
        supertrend_lower_exists = cur.fetchone()[0]

        if not (os_exists and supertrend_upper_exists and supertrend_lower_exists):
            logging.error("❌ Required columns 'os', 'supertrend_upper', or 'supertrend_lower' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, os, supertrend_upper, supertrend_lower FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Supertrend Pivot calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'os', 'supertrend_upper', 'supertrend_lower'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize the Supertrend Pivot column
        df['spt'] = 0.0

        # ✅ Calculate the Supertrend Pivot
        for i in range(len(df)):
            os = df.at[i, 'os']
            if os == 1:
                # Bullish: Use the Supertrend Lower Band as the pivot
                df.at[i, 'spt'] = df.at[i, 'supertrend_lower']
            else:
                # Bearish: Use the Supertrend Upper Band as the pivot
                df.at[i, 'spt'] = df.at[i, 'supertrend_upper']

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['spt'] = df['spt'].astype(float)  # Ensure proper float values

        # ✅ Update Supertrend Pivot values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET spt = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['spt'], row['timestamp']))

        conn.commit()
        logging.info("✅ Supertrend Pivot (spt) calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Supertrend Pivot: {e}")

# ✅ Run the function to calculate & update Supertrend Pivot
calculate_supertrend_pivot()



def calculate_max_channel():
    """
    Calculate the Max Channel incorporating the Supertrend Pivot (spt)
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='os');")
        os_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='close');")
        close_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='spt');")
        spt_exists = cur.fetchone()[0]

        if not (os_exists and close_exists and spt_exists):
            logging.error("❌ Required columns 'os', 'close', or 'spt' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, os, close, spt FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Max Channel calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'os', 'close', 'spt'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize the Max Channel column
        df['max_channel'] = 0.0

        # ✅ Calculate the Max Channel
        for i in range(len(df)):
            close = df.at[i, 'close']
            os = df.at[i, 'os']
            spt = df.at[i, 'spt']

            if i == 0:
                # Initialize Max Channel for the first row
                df.at[i, 'max_channel'] = close
            else:
                prev_max_channel = df.at[i - 1, 'max_channel']
                prev_os = df.at[i - 1, 'os']

                if close > spt:  # Price crosses the Supertrend Pivot
                    df.at[i, 'max_channel'] = max(prev_max_channel, close)
                elif os == 1:  # Bullish trend
                    df.at[i, 'max_channel'] = max(close, prev_max_channel)
                else:  # Bearish trend
                    df.at[i, 'max_channel'] = min(spt, prev_max_channel)

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['max_channel'] = df['max_channel'].astype(float)  # Ensure proper float values

        # ✅ Update Max Channel values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET max_channel = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['max_channel'], row['timestamp']))

        conn.commit()
        logging.info("✅ Max Channel calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Max Channel: {e}")

# ✅ Run the function to calculate & update Max Channel
calculate_max_channel()


def calculate_min_channel():
    """
    Calculate the Min Channel incorporating the Supertrend Pivot (spt)
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='os');")
        os_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='close');")
        close_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='spt');")
        spt_exists = cur.fetchone()[0]

        if not (os_exists and close_exists and spt_exists):
            logging.error("❌ Required columns 'os', 'close', or 'spt' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, os, close, spt FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Min Channel calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'os', 'close', 'spt'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is datetime format

        # ✅ Initialize the Min Channel column
        df['min_channel'] = 0.0

        # ✅ Calculate the Min Channel
        for i in range(len(df)):
            close = df.at[i, 'close']
            os = df.at[i, 'os']
            spt = df.at[i, 'spt']

            if i == 0:
                # Initialize Min Channel for the first row
                df.at[i, 'min_channel'] = close
            else:
                prev_min_channel = df.at[i - 1, 'min_channel']
                prev_os = df.at[i - 1, 'os']

                if close < spt:  # Price crosses below the Supertrend Pivot
                    df.at[i, 'min_channel'] = min(prev_min_channel, close)
                elif os == 0:  # Bearish trend
                    df.at[i, 'min_channel'] = min(close, prev_min_channel)
                else:  # Bullish trend
                    df.at[i, 'min_channel'] = max(spt, prev_min_channel)

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['min_channel'] = df['min_channel'].astype(float)  # Ensure proper float values

        # ✅ Update Min Channel values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET min_channel = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['min_channel'], row['timestamp']))

        conn.commit()
        logging.info("✅ Min Channel calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Min Channel: {e}")

# ✅ Run the function to calculate & update Min Channel
calculate_min_channel()


def calculate_supertrend_avg():
    """
    Calculate the Supertrend Average Channel using Max and Min Channels,
    and update it in the PostgreSQL database for the ohlc_5min table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Ensure required columns exist before calculation
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='max_channel');")
        max_channel_exists = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ohlc_5min' AND column_name='min_channel');")
        min_channel_exists = cur.fetchone()[0]

        if not (max_channel_exists and min_channel_exists):
            logging.error("❌ Required columns 'max_channel' or 'min_channel' not found in the ohlc_5min table. Ensure they are calculated first.")
            return

        # ✅ Retrieve Max and Min Channel Data from ohlc_5min table
        cur.execute("SELECT timestamp, max_channel, min_channel FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for Supertrend Average Channel calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'max_channel', 'min_channel'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is in datetime format

        # ✅ Calculate the Supertrend Average Channel
        df['supertrend_avg'] = (df['max_channel'] + df['min_channel']) / 2

        # ✅ Convert timestamp & values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['supertrend_avg'] = df['supertrend_avg'].astype(float)  # Ensure proper float values

        # ✅ Update Supertrend Average values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET supertrend_avg = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['supertrend_avg'], row['timestamp']))

        conn.commit()
        logging.info("✅ Supertrend Average Channel calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating Supertrend Average Channel: {e}")

# ✅ Run the function to calculate & update Supertrend Average Channel
calculate_supertrend_avg()


def calculate_5wma():
    """
    Calculate the 5-period Weighted Moving Average (5WMA) and update it in the PostgreSQL database
    for the ohlc_5min table.
    
    - Uses a **weighted sum** approach for the last 5 closing prices.
    - For the first 4 rows where 5WMA cannot be computed, **uses the close price instead**.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Retrieve OHLC Data from ohlc_5min table
        cur.execute("SELECT timestamp, close FROM ohlc_5min ORDER BY timestamp;")
        rows = cur.fetchall()

        if not rows:
            logging.warning("⚠️ No data found in ohlc_5min table for 5WMA calculation.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Ensure timestamp is in datetime format

        # ✅ Ensure required column exists
        if 'close' not in df.columns:
            logging.error("❌ Required column 'close' not found in the ohlc_5min table.")
            return

        # ✅ Define Weights
        weights = [1, 2, 3, 4, 5]

        # ✅ Calculate the 5-Period Weighted Moving Average (5WMA)
        df['5wma'] = df['close'].rolling(window=5).apply(lambda x: sum(w * c for w, c in zip(weights, x)) / sum(weights), raw=True)

        # ✅ Fill first 4 NaN values with the corresponding close price
        df['5wma'].fillna(df['close'], inplace=True)

        # ✅ Convert timestamp & 5WMA values for PostgreSQL compatibility
        df['timestamp'] = df['timestamp'].astype(str)  # Ensure proper string format
        df['5wma'] = df['5wma'].astype(float)  # Ensure proper float values

        # ✅ Update 5WMA values **row by row** in PostgreSQL
        update_query = "UPDATE ohlc_5min SET five_wma = %s WHERE timestamp = %s;"

        for _, row in df.iterrows():
            cur.execute(update_query, (row['5wma'], row['timestamp']))

        conn.commit()
        logging.info("✅ 5WMA calculated and updated successfully in ohlc_5min!")

        # ✅ Close connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error updating 5WMA: {e}")

# ✅ Run the function to calculate & update 5WMA
calculate_5wma()

import psycopg2
import logging

def calculate_rolling_5wma():
    """
    Calculates the rolling 5WMA using the last 5 five-minute closing prices
    and updates it in the 'rolling_5wma' column of the 'ohlc_1min' table.
    """
    try:
        # ✅ Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # ✅ Fetch the last 21 1-minute OHLC candles (to get the 5 required closing prices)
        cur.execute("""
            SELECT timestamp, close FROM ohlc_1min 
            ORDER BY timestamp DESC
            LIMIT 21;
        """)
        rows = cur.fetchall()

        if len(rows) < 21:
            logging.warning("⚠️ Not enough data to calculate rolling 5WMA. Need at least 21 rows.")
            return

        # ✅ Extract every 5th closing price for WMA calculation
        selected_closes = [rows[i][1] for i in [0, 5, 10, 15, 20]]  # 1st, 6th, 11th, 16th, 21st

        # ✅ Define Weights: [1,2,3,4,5]
        weights = [5, 4, 3, 2, 1]
        
        # ✅ Calculate Weighted Moving Average (5WMA)
        rolling_5wma = sum(w * c for w, c in zip(weights, selected_closes)) / sum(weights)

        # ✅ Get the latest timestamp (i.e., most recent 1-min candle)
        latest_timestamp = rows[0][0]

        # ✅ Update the rolling_5wma in the database for the latest timestamp
        cur.execute("""
            UPDATE ohlc_1min 
            SET rolling_5wma = %s 
            WHERE timestamp = %s;
        """, (rolling_5wma, latest_timestamp))

        conn.commit()
        logging.info(f"✅ Rolling 5WMA ({rolling_5wma:.2f}) updated for {latest_timestamp}")

        # ✅ Close DB connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error calculating rolling 5WMA: {e}")


#Setting up live websocket connection for tick by tick data fetching, aggregation and handling

from kiteconnect import KiteTicker
import logging
import time
import os
import datetime
from collections import defaultdict, deque

# ✅ Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Zerodha API Credentials
API_KEY = "8re7mjcm2btaozwf"  # Replace with your API key

# ✅ Fetch access token dynamically from the file
with open("access_token.txt", "r") as f:
    ACCESS_TOKEN = f.read().strip()

# ✅ Define Instrument Tokens for Subscription
INSTRUMENT_TOKENS = [256265]  #nat gas/nifty 50 index       112703495/256265

# ✅ Initialize KiteTicker WebSocket
kws = KiteTicker(API_KEY, ACCESS_TOKEN)

# ✅ Dictionary to Store Tick Buffers Indexed by Minute
tick_buffer = defaultdict(lambda: defaultdict(deque))  # {token: {minute: deque()}}
ohlc_data = {}

# ✅ Function to Kill Existing WebSocket Instances
def kill_existing_websockets():
    try:
        os.system("pkill -f kiteconnect")  # Kills existing WebSocket processes related to Kite
        logging.info("✅ Existing WebSocket instances killed successfully.")
    except Exception as e:
        logging.error(f"❌ Error while killing existing WebSocket processes: {e}")


# ✅ Tick Buffers for 1-Minute and 5-Minute OHLC Calculation
tick_buffer = defaultdict(lambda: defaultdict(deque))  # {token: {minute: deque()}}
tick_buffer_5min = defaultdict(lambda: deque())  # {token: deque()}

# ✅ Function to Process OHLC for a Given Minute and Store in PostgreSQL
def process_ohlc_candle():
    current_time = datetime.datetime.now()
    current_minute = current_time.strftime("%Y-%m-%d %H:%M")  # "YYYY-MM-DD HH:MM"

    try:
        # ✅ Connect to PostgreSQL (without redundant logging)
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        for token in INSTRUMENT_TOKENS:
            previous_minute = (current_time - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")

            # ✅ Process the Previous Minute's Data for 1-Minute OHLC
            if previous_minute in tick_buffer[token]:
                ticks = list(tick_buffer[token][previous_minute])  # Extract all ticks
                
                if ticks:
                    prices = [tick['last_price'] for tick in ticks]
                    ohlc_entry = {
                        "timestamp": previous_minute,
                        "open": prices[0],
                        "high": max(prices),
                        "low": min(prices),
                        "close": prices[-1]
                    }

                    logging.info(f"📊 1-min OHLC for {token}: {ohlc_entry}")

                    # ✅ Check if the timestamp already exists in the database
                    cur.execute("SELECT EXISTS(SELECT 1 FROM ohlc_1min WHERE timestamp = %s);", (previous_minute,))
                    exists = cur.fetchone()[0]

                    if not exists:
                        # ✅ Insert the new OHLC entry
                        cur.execute("""
                            INSERT INTO ohlc_1min (timestamp, open, high, low, close)
                            VALUES (%s, %s, %s, %s, %s);
                        """, (previous_minute, ohlc_entry["open"], ohlc_entry["high"], 
                              ohlc_entry["low"], ohlc_entry["close"]))
                        
                        conn.commit()
                        logging.info(f"✅ Inserted new 1-min OHLC candle for {token} into database.")
                        # ✅ Call `calculate_rolling_5wma()` AFTER inserting a new 1-min candle
                        calculate_rolling_5wma()
                    else:
                        logging.warning(f"⚠️ Duplicate OHLC timestamp detected: {previous_minute}. Skipping insertion.")

                # ✅ Store Ticks in 5-Minute Buffer (FOR 5-MIN CALCULATION)
                tick_buffer_5min[token].extend(ticks)

                # ✅ Clear Buffer for Processed 1-Minute Candle
                del tick_buffer[token][previous_minute]

        # ✅ Check if a New 5-Minute Window Has Started Based on System Time
        minute_value = current_time.minute
        if minute_value % 5 == 0:  # ✅ Only process at 5-minute intervals
            for token in INSTRUMENT_TOKENS:
                if len(tick_buffer_5min[token]) == 0:
                    continue  # Skip if no tick data for the last 5 minutes

                # ✅ Calculate Correct 5-Minute Start Time (Handles Hour Transitions)
                five_min_start = current_time - datetime.timedelta(minutes=5)  # Move back 5 min
                five_min_start = five_min_start.replace(second=0).strftime("%Y-%m-%d %H:%M")  # Ensure formatted timestamp

                # ✅ Extract Ticks from the Last 5 Minutes
                five_min_ticks = list(tick_buffer_5min[token])
                five_min_prices = [tick['last_price'] for tick in five_min_ticks]

                # ✅ Compute the 5-Minute OHLC
                five_min_entry = {
                    "timestamp": five_min_start,  # ✅ Corrected Timestamp (e.g., 12:00 instead of 12:05)
                    "open": five_min_prices[0],
                    "high": max(five_min_prices),
                    "low": min(five_min_prices),
                    "close": five_min_prices[-1]
                }

                logging.info(f"📊 5-min OHLC for {token}: {five_min_entry}")

                # ✅ Check if the timestamp already exists in the database
                cur.execute("SELECT EXISTS(SELECT 1 FROM ohlc_5min WHERE timestamp = %s);", (five_min_start,))
                exists = cur.fetchone()[0]

                if not exists:
                    # ✅ Insert the new 5-Min OHLC entry
                    cur.execute("""
                        INSERT INTO ohlc_5min (timestamp, open, high, low, close)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (five_min_start, five_min_entry["open"], five_min_entry["high"], 
                          five_min_entry["low"], five_min_entry["close"]))

                    conn.commit()
                    logging.info(f"✅ Inserted new 5-min OHLC candle for {token} at {five_min_start}.")

                    # ✅ Call functions to calculate indicators for the latest timestamp (WITH ARGUMENT PASSED CORRECTLY)
                    calculate_hl2()
                    calculate_atr()
                    calculate_initial_upper_band()
                    calculate_initial_lower_band()
                    calculate_supertrend_upper()
                    calculate_supertrend_lower()
                    calculate_oscillation_state()
                    calculate_supertrend_pivot()
                    calculate_max_channel()
                    calculate_min_channel()
                    calculate_supertrend_avg()
                    calculate_5wma()

                    logging.info(f"✅ Indicators calculated for latest 5-min timestamp: {five_min_start}")

                else:
                    logging.warning(f"⚠️ Duplicate 5-min OHLC timestamp detected: {five_min_start}. Skipping insertion.")

                # ✅ Clear Buffer for Processed 5-Minute Range
                tick_buffer_5min[token].clear()

        # ✅ Close database cursor and connection
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"❌ Error inserting OHLC data: {e}")
        if conn:
            conn.rollback()
            cur.close()
            conn.close()


# ✅ Handle WebSocket Connection
def on_connect(ws, response):
    logging.info("✅ WebSocket Connected. Attempting subscription...")

    try:
        time.sleep(1)  # Small delay before subscribing (prevents race condition)
        ws.subscribe(INSTRUMENT_TOKENS)
        logging.info(f"📡 Subscription request sent for: {INSTRUMENT_TOKENS}")

        ws.set_mode(ws.MODE_FULL, INSTRUMENT_TOKENS)
        logging.info(f"📡 Mode set to FULL for: {INSTRUMENT_TOKENS}")

        logging.info("🔄 WebSocket is now actively listening for tick data...")

    except Exception as e:
        logging.error(f"❌ Subscription failed: {e}")

# ✅ Handle Incoming Tick Data & Assign to Correct Minute
def on_ticks(ws, ticks):
    for tick in ticks:
        token = tick['instrument_token']
        tick_time = tick['exchange_timestamp'].strftime("%Y-%m-%d %H:%M")  # Extract minute part
        tick_buffer[token][tick_time].append(tick)  # Append tick to its respective minute

# ✅ Handle WebSocket Closure & Reconnection
def on_close(ws, code, reason):
    logging.warning(f"⚠️ WebSocket Closed: {code}, Reason: {reason}")
    logging.info("🔁 Reconnecting in 5 seconds...")
    time.sleep(5)
    ws.connect(reconnect=True)

# ✅ Handle WebSocket Errors
def on_error(ws, code, reason):
    logging.error(f"❌ WebSocket Error Occurred! Code: {code}, Reason: {reason}")

    if "token" in reason.lower():
        logging.error("🔴 Possible access token issue! Fetch a new one and restart.")

# ✅ Handle Reconnection Attempts
def on_reconnect(ws, attempts):
    logging.warning(f"🔄 Reconnecting... Attempt {attempts}")

# ✅ Assign Event Handlers to WebSocket
kws.on_connect = on_connect
kws.on_ticks = on_ticks
kws.on_close = on_close
kws.on_error = on_error
kws.on_reconnect = on_reconnect

# ✅ Start WebSocket After Killing Any Existing Ones
kill_existing_websockets()
logging.info("🚀 Starting WebSocket...")
kws.connect(threaded=True)

# ✅ Process OHLC Data Every Second
while True:
    process_ohlc_candle()
    # process_5min_ohlc()
    time.sleep(1)
