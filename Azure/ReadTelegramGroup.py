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
from datetime import datetime, timezone

# Your api_id and api_hash from my.telegram.org
api_id = '21789309'
api_hash = '25cfde9a425a3658172d011e45e81a2c'
phone = '+2784583071'  # e.g. +123456789

bot_token = '6695292881:AAHoEsUyrgkHAYqsbXcn9XWN9Y7nNTi5Jy4'
JDBCopyTrading_chat_id = '-1001920185934'
JDBPrivate_chat_id = '-1001920185934'

# HTTP server URL for POST requests
http_server_url = 'http://127.0.0.1:9094/'  # Change this to your HTTP server URL

# Create the client and connect
client = TelegramClient('session_name', api_id, api_hash)

# Magic numbers for each group
group_magic_numbers = {
    'Gold Scalper Ninja': 2784583072,
    'FABIO VIP SQUAD': 2784583073,
    'THE FOREX BOAR 🚀': 2784583074,
    'JDB Copy Signals': 2784583075
}

def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
    }
    response = requests.post(url, data=data)
    return response.json()

async def send_http_post_message(session, trade_type, symbol, sl, tp, tp_number):
    print("Send HTTP POST message")
    data = {
        "Code": "Place Trade",
        "Type": trade_type,
        "Symbol": symbol,
        "SL": sl,
        "TP": tp,
        "TP_Number": tp_number
    }
    print(data)
    
    try:
        async with session.post(http_server_url, json=data) as response:
            if response.status != 200:
                print(f"HTTP POST failed with status {response.status}")
            else:
                print(f"HTTP POST successful: {response.status}")
    except aiohttp.ClientResponseError as e:
        print(f"Client response error: {e}")
    except aiohttp.ClientConnectionError as e:
        print(f"Client connection error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def placeOrder(symbol, trade_type, sl, tp, magic_number):
    print(f"Place order {symbol} {trade_type} TP: {tp} SL: {sl} Magic: {magic_number}")
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found")
    else:
        print(f"Symbol {symbol} found")
        price = 0

        if trade_type == "Buy Limit":
            order_type = mt5.ORDER_TYPE_BUY_LIMIT
        elif trade_type == "Sell Limit":
            order_type = mt5.ORDER_TYPE_SELL_LIMIT
        elif trade_type == "Buy":
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
        elif trade_type == "Sell":
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
        else:
            print(f"Unsupported trade type: {trade_type}")
            return
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": symbol_info.volume_min,
            "type": order_type,
            "price": price,
            "tp": float(tp),
            "sl": float(sl),
            "magic": magic_number,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        order_result = mt5.order_send(request)
        if order_result.retcode != mt5.TRADE_RETCODE_DONE:
            print("Error placing order:", order_result.comment)
        else:
            print("Order placed successfully")

async def process_group_messages(group_name, start_date, session):
    entity = None
    async for dialog in client.iter_dialogs():
        if dialog.name == group_name:
            entity = dialog.entity
            break

    if not entity:
        print(f"Error: Could not find the group '{group_name}'. Please check the group name.")
        return

    channel = entity
    last_message_id = 0
    magic_number = group_magic_numbers.get(group_name, 2784583072)

    while True:
        try:
            result = await client(GetHistoryRequest(
                peer=PeerChannel(channel.id),
                limit=1,  # Fetch the latest message
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))

            messages = result.messages
            if messages:
                latest_message = messages[0]
                message_date = latest_message.date.replace(tzinfo=timezone.utc)

                if latest_message.id != last_message_id and message_date >= start_date:
                    message_text = latest_message.message.upper()  # Convert message to uppercase
                    message_date_str = message_date.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{group_name}: {message_text} at {message_date_str}")

                    def parse_message(text):
                        trade_type = None
                        if "SELL LIMIT" in text:
                            trade_type = "Sell Limit"
                        elif "BUY LIMIT" in text:
                            trade_type = "Buy Limit"
                        elif "SELL" in text and "LIMIT" not in text:
                            trade_type = "Sell"
                        elif "BUY" in text and "LIMIT" not in text:
                            trade_type = "Buy"

                        symbol = None
                        if "XAUUSD" in text:
                            symbol = "GOLD"
                        elif "GOLD" in text:
                            symbol = "GOLD"

                        sl_line = [line for line in text.split('\n') if 'SL' in line or 'SL‼️' in line]
                        sl = sl_line[0].split(':')[-1].strip() if sl_line else None
                        sl = re.sub(r'[^\d.]', '', sl) if sl else None  # Keep only numeric characters and dot

                        tp_lines = [line for line in text.split('\n') if 'TP' in line]
                        tps = [re.sub(r'[^\d.]', '', line.split(':')[-1].strip()) for line in tp_lines]  # Keep only numeric characters and dot

                        return trade_type, symbol, sl, tps

                    async def parse_and_send_messages(message_text):
                        try:
                            trade_type, symbol, sl, tps = parse_message(message_text)

                            if trade_type and symbol and sl and tps:
                                for i, tp in enumerate(tps):
                                    if i < 4 and tp:  # Ensure we only handle up to 4 TPs and TP is not empty
                                        message = f"{trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nFrom: {group_name}\nDate: {message_date_str}"
                                        send_telegram_message(JDBCopyTrading_chat_id, message)
                                        #asyncio.create_task(send_http_post_message(session, trade_type, symbol, sl, tp, i+1))
                                        placeOrder(symbol, trade_type, sl, tp, magic_number)
                        except IndexError:
                            print(f"Error parsing message from {group_name}: {message_text}")
                        except Exception as e:
                            print(f"Unexpected error: {e}")

                    await parse_and_send_messages(message_text)

                    last_message_id = latest_message.id

        except Exception as e:
            print(f"Error processing group {group_name}: {e}")

        # Wait for 10 seconds before checking again
        await asyncio.sleep(10)

def InitializeAccounts():
    print("----------InitializeAccounts---------")
    
    PATH = os.path.abspath(__file__)
    DIRECTORY = os.path.dirname(os.path.dirname(PATH))
    dbPath = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")
    
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
            print("Failed to initialize MT5 terminal from", instance_path)
            print("Error:", mt5.last_error())
        else:
            print("MT5 initialized successfully for account ID:", row[0])

    db_conn.close()

async def main():
    InitializeAccounts()
    await client.start(phone)
    print("Client Created")

    # List of group names to monitor
    group_names = ['Gold Scalper Ninja', 'FABIO VIP SQUAD', 'THE FOREX BOAR 🚀', 'JDB Copy Signals']

    # Start date to filter messages
    start_date = datetime.now(timezone.utc)

    async with aiohttp.ClientSession() as session:
        # Start a task for each group
        tasks = [process_group_messages(group_name, start_date, session) for group_name in group_names]
        await asyncio.gather(*tasks)

with client:
    client.loop.run_until_complete(main())
