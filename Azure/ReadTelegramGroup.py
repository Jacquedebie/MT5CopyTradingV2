from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import asyncio
import requests
import aiohttp
import MetaTrader5 as mt5
import os
import re
import sqlite3
import traceback

from datetime import datetime, timezone, timedelta

PATH = os.path.abspath(__file__)
DIRECTORY = os.path.dirname(os.path.dirname(PATH))
dbPath = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

lotSizeToUse = 0.01
preProd = True
takeAllTrades = False

# Your api_id and api_hash from my.telegram.org
#JDB
if preProd:
    api_id = '21789309'
    api_hash = '25cfde9a425a3658172d011e45e81a2c'
    phone = '+2784583071'  # e.g. +123456789
else:
    #JW
    api_id = '21265406'
    api_hash = 'aed729c24e62f0aa55e263ca153bbc3e'
    phone = '+27744183636'  # e.g. +123456789


bot_token = '6695292881:AAHoEsUyrgkHAYqsbXcn9XWN9Y7nNTi5Jy4'
JDBCopyTrading_chat_id = '-1001920185934'
JDBPrivate_chat_id = '-1001920185934'

# HTTP server URL for POST requests
http_server_url = 'http://127.0.0.1:9094/'  # Change this to your HTTP server URL
refreshList = 5  # Refresh the list every 5 minutes
sameSignalCount = 5  # Number of same signals before placing a trade
# Create the client and connect
client = TelegramClient('session_name', api_id, api_hash)


groups_info = {}

# List of symbols to look for
symbols = ['XAUUSD', 'GOLD' , 'XAU/USD']  # Add more symbols as needed
#'BTCUSD', spread is te hoog
#, 'EURUSD', 'GBPUSD', 'USDJPY', 'EURJPY', 'GBPJPY', 'GBPNZD', 'USOIL', 'USDCAD' Focus net op GOUD

# Dictionary to track counts and timestamps
trade_tracker = {}

def print_to_console_and_file(message):
    with open(os.path.join(DIRECTORY, "TelegramOutput.txt"), "a", encoding="utf-8") as outputfile:
        print(message, file=outputfile)  # Print to the file
    print(message)  # Print to the console


def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
    }
    response = requests.post(url, data=data)
    return response.json()

def is_valid_sl(price, sl, trade_type, symbol_info):
    # Ensure price and SL are floats for comparison
    price = float(price)
    sl = float(sl)
    
    # Access the stop level; default to 0 if not available
    stop_level = symbol_info.trade_stops_level if hasattr(symbol_info, 'trade_stops_level') else 0

    # Adjust the logic based on trade type
    if  stop_level == 0:
        return False
    elif trade_type == "Buy" or trade_type == "Buy Limit":
        return sl < price and (price - sl) >= stop_level * symbol_info.point
    elif trade_type == "Sell" or trade_type == "Sell Limit":
        return sl > price and (sl - price) >= stop_level * symbol_info.point
    return False

def placeOrder(symbol, trade_type, sl, tp, price, magic_number, group_name):
    print_to_console_and_file(f"Place order {symbol} {trade_type} TP: {tp} SL: {sl} Price: {price} Magic: {magic_number}")

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print_to_console_and_file(f"Symbol {symbol} not found")
        return False

    # Check if an order with the same magic number, TP, and SL already exists
    orders = mt5.orders_get(symbol=symbol)
    for order in orders:
        if order.magic == magic_number and order.tp == tp: #and order.sl == sl
            print_to_console_and_file(f"Order with Magic: {magic_number}, TP: {tp}, SL: {sl} already exists. Skipping order placement.")
            return False
        
    # If price is None, assign the current market price based on trade type
    if price is None:
        if trade_type == "Buy" or trade_type == "Buy Limit":
            price = symbol_info.ask
            print_to_console_and_file(f"Price is None. Setting price to current ask: {price}")
        elif trade_type == "Sell" or trade_type == "Sell Limit":
            price = symbol_info.bid
            print_to_console_and_file(f"Price is None. Setting price to current bid: {price}")
        else:
            print_to_console_and_file(f"Unsupported trade type: {trade_type}")
            return False

    # Ensure price, sl, and tp are floats
    price = float(price)
    sl = float(sl)
    tp = float(tp)

    # Check if SL is valid
    if not is_valid_sl(price, sl, trade_type, symbol_info):
        print_to_console_and_file(f"Invalid SL: {sl} for {trade_type} order at {price}. Adjusting or skipping order.")
        #Check if NEW SL is more than prevois cannot be snammer
        if trade_type == "Buy" or trade_type == "Buy Limit":
            sl = price - (500 * symbol_info.point)
        elif trade_type == "Sell" or trade_type == "Sell Limit":
            sl = price + (500 * symbol_info.point)

        print_to_console_and_file(f"New SL set to {sl}")
        # You may choose to return False here to skip placing the order if SL is invalid.
        # return False 

    # Adjust price according to the trade type
    if trade_type == "Buy Limit":
        order_type = mt5.ORDER_TYPE_BUY_LIMIT
        if price > symbol_info.ask:
            print_to_console_and_file(f"Incorrect price for Buy Limit. Adjusting price from {price} to {symbol_info.ask}")
            price = symbol_info.ask
    elif trade_type == "Sell Limit":
        order_type = mt5.ORDER_TYPE_SELL_LIMIT
        if price < symbol_info.bid:
            print_to_console_and_file(f"Incorrect price for Sell Limit. Adjusting price from {price} to {symbol_info.bid}")
            price = symbol_info.bid
    elif trade_type == "Buy":
        order_type = mt5.ORDER_TYPE_BUY
        if price != symbol_info.ask:
            print_to_console_and_file(f"Incorrect price for Buy. Adjusting price from {price} to {symbol_info.ask}")
            price = symbol_info.ask
    elif trade_type == "Sell":
        order_type = mt5.ORDER_TYPE_SELL
        if price != symbol_info.bid:
            print_to_console_and_file(f"Incorrect price for Sell. Adjusting price from {price} to {symbol_info.bid}")
            price = symbol_info.bid
    else:
        print_to_console_and_file(f"Unsupported trade type: {trade_type}")
        return False

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lotSizeToUse),
        "type": order_type,
        "price": float(price),
        "tp": float(tp),
        "sl": float(sl),
        "magic": magic_number,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "comment": group_name
    }

    order_result = mt5.order_send(request)
    if order_result.retcode != mt5.TRADE_RETCODE_DONE:
        print_to_console_and_file("Error placing order:" + order_result.comment)
        return False
    else:
        print_to_console_and_file("Order placed successfully")
        return True

async def process_all_group_messages(start_date, session):
    entities = {}
    for group_name in groups_info.keys():
        async for dialog in client.iter_dialogs():
            if dialog.name == group_name:
                entities[group_name] = dialog.entity
                break

    if not entities:
        print_to_console_and_file(f"Error: Could not find any of the groups. Please check the group names.")
        return

    last_message_ids = {group_name: 0 for group_name in entities}
    while True:
        try:
            for group_name, entity in entities.items():
                magic_number = groups_info[group_name]
                result = await client(GetHistoryRequest(
                    peer=PeerChannel(entity.id),
                    limit=100,  # Fetch up to 100 messages at a time
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                ))

                messages = result.messages
                if messages:
                    for message in messages:
                        message_date = message.date.replace(tzinfo=timezone.utc)

                        if message.id != last_message_ids[group_name] and message_date >= start_date:
                            if message.message is not None:  # Check if the message is not None
                                message_text = message.message.upper()  # Convert message to uppercase

                                if "VIP GROUP OPEN FOR" in message_text:
                                    print_to_console_and_file(f"Skipping trade from {group_name} due to 'VIP GROUP OPEN FOR' in the message.")
                                    continue  # Skip processing this message

                                message_date_str = message_date.strftime('%Y-%m-%d %H:%M:%S')
                                print_to_console_and_file(f'--------------{group_name}-------------------')
                                print_to_console_and_file(f"{group_name}: {message_text} at {message_date_str}")
                                print_to_console_and_file('---------------------------------')
                                
                                def parse_message(text):
                                    trade_type = None
                                    price = None
                                    
                                    # Determine trade type
                                    if "SELL LIMIT" in text:
                                        trade_type = "Sell Limit"
                                    elif "BUY LIMIT" in text:
                                        trade_type = "Buy Limit"
                                    elif "SELL" in text and "LIMIT" not in text:
                                        trade_type = "Sell"
                                    elif "BUY" in text and "LIMIT" not in text:
                                        trade_type = "Buy"

                                    # Determine symbol
                                    symbol = None
                                    symbols = ['XAU/USD', 'XAUUSD', 'USOIL','GOLD']  # Add other symbols as needed
                                    for sym in symbols:
                                        if sym in text:
                                            symbol = sym
                                            break
                                    
                                    # Map symbol to internal representation
                                    if symbol == "USOIL":
                                        symbol = "XBRUSD"
                                    elif symbol == "XAUUSD" or symbol == "XAU/USD":
                                        symbol = "GOLD"

                                    # Find stop loss lines
                                    sl_keywords = ['SL', 'STOP LOSS', 'STOPLOSS']
                                    sl_line = [line for line in text.split('\n') if any(kw in line.upper() for kw in sl_keywords)]
                                    
                                    # Extract the stop loss value
                                    sl = None
                                    if sl_line:
                                        sl_match = re.search(r'\d{1,5}(?:\.\d+)?', sl_line[0])
                                        if sl_match:
                                            sl = float(sl_match.group().lstrip('.'))

                                    # Find take profit lines
                                    tp_keywords = ['TP', 'TAKE PROFIT', 'TAKEPROFIT']
                                    tp_lines = [line for line in text.split('\n') if any(kw in line.upper() for kw in tp_keywords)]
                                    
                                    # Extract the TP values from those lines
                                    tps = []
                                    for line in tp_lines:
                                        match = re.search(r'\d{3,5}(?:\.\d+)?', line)
                                        if match:
                                            tps.append(float(match.group()))

                                    # Extract the trade entry price (if it doesn't match SL or any TP)
                                    price_candidates = re.findall(r'\d{3,5}\.\d+', text)
                                    if price_candidates:
                                        for candidate in price_candidates:
                                            candidate_price = float(candidate)
                                            if candidate_price not in tps and (sl is None or candidate_price != sl):
                                                price = candidate_price
                                                break
                                    
                                    return trade_type, symbol, sl, tps, price

                                async def parse_and_send_messages(message_text):
                                    try:
                                        trade_type, symbol, sl, tps, price = parse_message(message_text)
                                        print_to_console_and_file(f'trade_type: {trade_type} symbol: {symbol} sl: {sl} tps: {tps} price: {price}')
                                        if trade_type and symbol and sl and tps:
                                            # Only log when a TP and SL are given
                                            if sl and tps:
                                                for i, tp in enumerate(tps):    
                                                    if i < 4 and tp:  # Ensure we only handle up to 4 TPs and TP is not empty
                                                        if preProd:
                                                            message = f"Actual TRADE OUTSIDE OF COUNTER\nFrom: {group_name}\ntrade_type: {trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nDate: {message_date_str}"
                                                        else:
                                                            message = f"PROD!!!!\nActual TRADE OUTSIDE OF COUNTER\nFrom: {group_name}\ntrade_type: {trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nDate: {message_date_str}"
                                                        if placeOrder(symbol, trade_type, sl, tp, price, magic_number,group_name):
                                                            send_telegram_message(JDBCopyTrading_chat_id, message)
                                                        else:
                                                            print_to_console_and_file("Failed to place order")
                                                        
                                                    if not takeAllTrades:
                                                        break
                                                            
                                    except IndexError:
                                        print_to_console_and_file(f"Error parsing message from {group_name}: {message_text}")
                                    except Exception as e:
                                        tb = traceback.format_exc()

                                        message = (
                                            f"Unexpected error: {e}\n"
                                            f"From: {group_name if 'group_name' in locals() or 'group_name' in globals() else '[unknown]'}\n"
                                            f"trade_type: {trade_type if 'trade_type' in locals() or 'trade_type' in globals() else '[unknown]'}\n"
                                            f"Symbol: {symbol if 'symbol' in locals() or 'symbol' in globals() else '[unknown]'}\n"
                                            f"SL: {sl if 'sl' in locals() or 'sl' in globals() else '[unknown]'}\n"
                                            f"TP: {tp if 'tp' in locals() or 'tp' in globals() else '[unknown]'}\n"
                                            f"Date: {message_date_str if 'message_date_str' in locals() or 'message_date_str' in globals() else '[unknown]'}\n"
                                            f"Traceback:\n{tb}"  # Include the full traceback, which contains the line number
                                        )
                                        print_to_console_and_file(message)


                                await parse_and_send_messages(message_text)

                                last_message_ids[group_name] = message.id

        except Exception as e:
            print_to_console_and_file(f"Error processing group messages: {e}")

        # Wait for 10 seconds before checking again
        await asyncio.sleep(10)



#Telegram Groups
def populate_telegram_groups():
    global groups_info
    
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tbl_telegramGroups_GroupName, tbl_telegramGroup_MagicNumber 
        FROM tbl_telegramGroups
        WHERE tbl_telegramGroup_ActiveIndicator = 1
    """)
    rows = cursor.fetchall()

    groups_info = {row[0]: row[1] for row in rows}

    conn.close()

async def updateTelegramGroups():
    while True:
        print_to_console_and_file("Telegram groups updated")  # Replace this with the actual function you want to run
        populate_telegram_groups()
        await asyncio.sleep(3600)  # Sleep for 5 seconds for testing, change to 3600 for 1 hour

def InitializeAccounts():
    print_to_console_and_file("----------InitializeAccounts---------")

    DB_CONNECTION = dbPath

    db_conn = sqlite3.connect(DB_CONNECTION)

    db_cursor = db_conn.cursor()

    # get main account
    db_cursor.execute("SELECT tbl_account_id, tbl_account_password, tbl_account_server, tbl_account_name FROM tbl_account WHERE tbl_account_active = 1 AND tbl_account_mainaccount = 0")
    counter = 0
    for row in db_cursor.fetchall():
        counter = counter + 1
        # MAIN
        instance_path = os.path.join(DIRECTORY, "Instances", str(2), "terminal64.exe")

        if not mt5.initialize(login=int(row[0]), password=row[1], server=row[2], path=instance_path):
            print_to_console_and_file("Failed to initialize MT5 terminal from " + instance_path)
            print_to_console_and_file(f"Error: {mt5.last_error()}")
        else:
            print_to_console_and_file(f"MT5 initialized successfully for account ID: {row[0]}")

    db_conn.close()

#Function call on startup
populate_telegram_groups()
print_to_console_and_file(groups_info)

async def main():

    update_task = asyncio.create_task(updateTelegramGroups())

    InitializeAccounts()
    await client.start(phone)
    print_to_console_and_file("Client Created")

    # Start date to filter messages
    start_date = datetime.now(timezone.utc)
    
    async with aiohttp.ClientSession() as session:
        await process_all_group_messages(start_date, session)

    await update_task

with client:
    client.loop.run_until_complete(main())
