import MetaTrader5 as mt5
import sqlite3
from datetime import datetime, timedelta

# Database path
db_path = r"C:\Users\Janco.Weyers\Desktop\MT5CopyTradingV2\DataBases\CopyTradingV2.db"
conn = sqlite3.connect(db_path)

cursor = conn.cursor()

# Connect to MetaTrader 5
if not mt5.initialize():
    print("Failed to initialize MT5:", mt5.last_error())
    mt5.shutdown()
    exit()

# Set your login details
login_id = 97576996  # replace with your MT5 login ID
password = '*EgU9P2R#p*dNyV'  # replace with your MT5 password
server = 'XMGlobal-MT5 5'  # replace with your MT5 broker server

# Login to the MT5 account
if not mt5.login(login_id, password=password, server=server):
    print("Failed to login to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()

# Define date range for fetching trades
to_date = datetime.now()
from_date = to_date - timedelta(days=7)  # modify as needed

# Retrieve trade history
trades = mt5.history_deals_get(from_date, to_date)
if trades is None:
    print("No trade history, error code:", mt5.last_error())
else:
    print(f"Retrieved {len(trades)} trades")

    # Insert trades into the database, ensuring no duplicates
    for trade in trades:
        # Check if trade ticket already exists in the database
        cursor.execute("SELECT 1 FROM tbl_trade WHERE tbl_trade_ticket = ?", (trade.ticket,))
        if cursor.fetchone():
            print(f"Trade with ticket {trade.ticket} already exists, skipping.")
            continue

        # Prepare trade data for insertion, with default values for missing attributes
        trade_data = (
            login_id,  # Assuming the current account ID as tbl_trade_account
            str(trade.ticket),  # Trade ticket as TEXT
            str(getattr(trade, 'magic', '0')),  # Trade magic, default to '0' if missing
            trade.volume,
            trade.profit,
            trade.symbol,
            0,  # Placeholder for tbl_trade_billed, assuming 0 or modify as needed
            datetime.fromtimestamp(trade.time).strftime('%Y-%m-%d %H:%M:%S'),
            datetime.fromtimestamp(trade.time_msc / 1000).strftime('%Y-%m-%d %H:%M:%S') if trade.time_msc else None,
            trade.type,
            getattr(trade, 'swap', 0.0),  # Swap, default to 0.0 if missing
            getattr(trade, 'drawdown', 0.0),  # Drawdown, default to 0.0 if missing
            getattr(trade, 'max_profit', 0.0),  # MaxProfit, default to 0.0 if missing
            trade.price,
            getattr(trade, 'tp', 0.0),  # Take Profit, default to 0.0 if missing
            getattr(trade, 'sl', 0.0),  # Stop Loss, default to 0.0 if missing
            getattr(trade, 'tsl', 0.0)  # Trailing Stop Loss, default to 0.0 if missing
        )

        # Insert trade into the database
        cursor.execute('''
        INSERT INTO tbl_trade (
            tbl_trade_account, tbl_trade_ticket, tbl_trade_magic, tbl_trade_volume,
            tbl_trade_profit, tbl_trade_symbol, tbl_trade_billed, tbl_trade_timeOpen,
            tbl_trade_timeClose, tbl_trade_type, tbl_trade_swap, tbl_trade_drawdown,
            tbl_trade_maxProfit, tbl_trade_price, tbl_trade_tp, tbl_trade_sl, tbl_trade_tsl
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', trade_data)

    conn.commit()

# Clean up
conn.close()
mt5.shutdown()
print("All new trades have been written to the database.")
