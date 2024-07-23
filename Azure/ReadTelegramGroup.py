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
from datetime import datetime, timezone, timedelta

PATH = os.path.abspath(__file__)
DIRECTORY = os.path.dirname(os.path.dirname(PATH))
dbPath = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

# Your api_id and api_hash from my.telegram.org
api_id = '21789309'
api_hash = '25cfde9a425a3658172d011e45e81a2c'
phone = '+2784583071'  # e.g. +123456789

bot_token = '6695292881:AAHoEsUyrgkHAYqsbXcn9XWN9Y7nNTi5Jy4'
JDBCopyTrading_chat_id = '-1001920185934'
JDBPrivate_chat_id = '-1001920185934'

# HTTP server URL for POST requests
http_server_url = 'http://127.0.0.1:9094/'  # Change this to your HTTP server URL
refreshList = 5  # Refresh the list every 5 minutes
sameSignalCount = 5  # Number of same signals before placing a trade
# Create the client and connect
client = TelegramClient('session_name', api_id, api_hash)


#populate telegram groups
print("----------Populate Telegram Groups---------")

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

# Dictionary to maintain group names and their corresponding magic numbers
# groups_info = {
#     'JDB Copy Trading Counter': 2784583071,
#     'Gold Scalper Ninja': 2784583072,
#     'FABIO VIP SQUAD': 2784583073,
#     'THE FOREX BOAR 🚀': 2784583074,
#     'JDB Copy Signals': 2784583075,
#     'JDB Copy Signals2': 2784583076,
#     'JDB Copy Signals3': 2784583077,
#     'JDB Copy Signals4': 2784583078,
#     '‎سيد تجارة الفوركس': 2784583079,
#     'GOLD FATHER CHRIS': 2784583080,
#     '𝘍𝘰𝘳𝘦𝘹 𝘎𝘰𝘭𝘥 𝘔𝘢𝘴𝘵𝘦𝘳': 2784583081,
#     '𝗚𝗢𝗟𝗗 𝗣𝗥𝗢 𝗧𝗥𝗔𝗗𝗘𝗥': 2784583082,
#     '𝘼𝙇𝙀𝙓 𝙓𝘼𝙐𝙐𝙎𝘿 𝘾𝙃𝘼𝙎𝙀𝙍 ➤': 2784583083,
#     'FOREX EMPIRE': 2784583084,
#     'GBPUSD+USDJPY(GOLD) SIGNALS': 2784583085,
#     'Loi\'s Gold TradingRoom': 2784583086,
#     'DENMARKPFOREX': 2784583087,
#     'Gold Snipers Fx - Free Gold Signals': 2784583088,
#     '𝐆𝐎𝐋𝐃 𝐓𝐑𝐀𝐃𝐈𝐍𝐆 𝐀𝐂𝐀𝐃𝐄𝐌𝐘': 2784583089,
#     'Forex Scalping Strategy 📈': 2784583090,
#     'Mr Beast Gold': 2784583091,
#     'Areval Forex™': 2784583092,
#     'FX UNIQUE TRADE 😍😍😍': 2784583093,
#     '🍀KING GOLD FOREX🍀🍀': 2784583094,
#     'King Of Gold⚡️': 2784583095,
#     'GOLD MASTER': 2784583096,
#     'FOREX TRADING SIGNAL(free)': 2784583097,
#     'XAUUSD GBPUSD': 2784583098,
#     'Chef Hazzim Scalping Maut🏆': 2784583099,
#     'Exnees account manager': 2784583100,
#     '𝙂𝙤𝙡𝙙 𝘽𝙡𝙪𝙚 𝙥𝙞𝙥𝙨 ®': 2784583101,
#     'MXGOLDTRADE': 2784583102,
#     'FOREX CHAMPION': 2784583103,
#     'Forex Signals🔥💰 XAUUSD': 2784583104,
#     '🔰PREMIUM Fx Signals💯': 2784583105,
#     '𝐅𝐎𝐑𝐄𝐗 𝐕𝐈𝐏 𝐓𝐑𝐀𝐃𝐈𝐍𝐆™ ⚡️': 2784583106,
#     'Daily Forex Signals': 2784583107,
#     'APEX BULL FO®EX SIGNALS (free)': 2784583108,
#     'Barclays Forex®': 2784583109,
#     'GOLD FX SIGNALS': 2784583110,
#     '𝐂𝐀𝐏𝐓𝐀𝐈𝐍 𝐅𝐎𝐑𝐄𝐗 𝐓𝐑𝐀𝐃𝐈𝐍𝐆': 2784583111,
#     'Gold signal killer pips': 2784583112
# }

# List of symbols to look for
symbols = ['XAUUSD', 'GOLD', 'EURUSD', 'GBPUSD', 'USDJPY', 'EURJPY', 'GBPJPY', 'GBPNZD', 'USOIL', 'USDCAD']  # Add more symbols as needed
#'BTCUSD', spread is te hoog

# Dictionary to track counts and timestamps
trade_tracker = {}

def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
    }
    response = requests.post(url, data=data)
    return response.json()

def placeOrder(symbol, trade_type, sl, tp, price, magic_number):
    print(f"Place order {symbol} {trade_type} TP: {tp} SL: {sl} Price: {price} Magic: {magic_number}")
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found")
        return False

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
        return False

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": symbol_info.volume_min,
        "type": order_type,
        "price": float(price),
        "tp": float(tp),
        "sl": float(sl),
        "magic": magic_number,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    order_result = mt5.order_send(request)
    if order_result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Error placing order:", order_result.comment)
        return False
    else:
        print("Order placed successfully")
        return True


async def process_all_group_messages(start_date, session):
    entities = {}
    for group_name in groups_info.keys():
        async for dialog in client.iter_dialogs():
            if dialog.name == group_name:
                entities[group_name] = dialog.entity
                break

    if not entities:
        print(f"Error: Could not find any of the groups. Please check the group names.")
        return

    last_message_ids = {group_name: 0 for group_name in entities}
    while True:
        try:
            # Remove the unused variable

            for group_name, entity in entities.items():
                magic_number = groups_info[group_name]
                result = await client(GetHistoryRequest(
                    peer=PeerChannel(entity.id),
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

                    if latest_message.id != last_message_ids[group_name] and message_date >= start_date:
                        if latest_message.message is not None:  # Check if the message is not None
                            message_text = latest_message.message.upper()  # Convert message to uppercase
                            message_date_str = message_date.strftime('%Y-%m-%d %H:%M:%S')
                            print(f'--------------{group_name}-------------------')
                            print(f"{group_name}: {message_text} at {message_date_str}")
                            print('---------------------------------')
                            
                            def parse_message(text):
                                trade_type = None
                                price = None
                                if "SELL LIMIT" in text:
                                    trade_type = "Sell Limit"
                                elif "BUY LIMIT" in text:
                                    trade_type = "Buy Limit"
                                elif "SELL" in text and "LIMIT" not in text:
                                    trade_type = "Sell"
                                    price_line = re.findall(r"\d+\.\d+", text)
                                    if price_line:
                                        price = float(price_line[0])
                                elif "BUY" in text and "LIMIT" not in text:
                                    trade_type = "Buy"
                                    price_line = re.findall(r"\d+\.\d+", text)
                                    if price_line:
                                        price = float(price_line[0])

                                symbol = None
                                for sym in symbols:
                                    if sym in text:
                                        symbol = sym
                                        break
                                
                                if symbol == "USOIL":
                                    symbol = "XBRUSD"
                                elif symbol == "XAUUSD":
                                    symbol = "GOLD"
                                    
                                sl_line = [line for line in text.split('\n') if 'SL' in line or 'SL‼️' in line]
                                sl = sl_line[0].split(':')[-1].strip() if sl_line else None
                                sl = re.sub(r'[^\d.]', '', sl) if sl else None  # Keep only numeric characters and dot

                                # Remove any leading periods
                                if sl and sl.startswith('.'):
                                    sl = sl[1:]
                                    
                                tp_lines = [line for line in text.split('\n') if 'TP' in line]
                                tps = [
                                    re.sub(r'^\.', '', re.sub(r'[^\d.]', '', line.split(':')[-1].strip()))
                                    for line in tp_lines
                                ]
                                return trade_type, symbol, sl, tps, price

                            async def parse_and_send_messages(message_text):
                                try:
                                    trade_type, symbol, sl, tps, price = parse_message(message_text)

                                    if trade_type and symbol and sl and tps:
                                        if price and trade_type in ["Buy", "Sell"]:
                                            symbol_info = mt5.symbol_info(symbol)
                                            if symbol_info:
                                                if trade_type == "Buy" and price < symbol_info.bid:
                                                    trade_type = "Buy Limit"
                                                elif trade_type == "Sell" and price > symbol_info.ask:
                                                    trade_type = "Sell Limit"

                                        # Only log when a TP and SL are given
                                        if sl and tps:
                                            # Tracking trade counts
                                            key = (symbol, trade_type)
                                            now = datetime.now(timezone.utc)
                                            if key not in trade_tracker:
                                                trade_tracker[key] = {'count': 0, 'first_entry': now, 'groups': set()}
                                            
                                            if magic_number not in trade_tracker[key]['groups']:
                                                trade_tracker[key]['count'] += 1
                                                trade_tracker[key]['groups'].add(magic_number)
                                            
                                            # Expire old entries
                                            for k, v in list(trade_tracker.items()):
                                                if (now - v['first_entry']) > timedelta(minutes=refreshList):
                                                    del trade_tracker[k]
                                            
                                            if trade_tracker[key]['count'] > sameSignalCount:
                                                print(f'------------------More than {sameSignalCount} same symbol----------------------------')
                                                print(f"Threshold exceeded for {symbol} {trade_type}")
                                                print('----------------------------------------------')
                                                trade_tracker[key]['count'] = 0
                                                trade_tracker[key]['groups'].clear()

                                                #This wil place the Trade from the Originator
                                                for i, tp in enumerate(tps):    
                                                    if i < 4 and tp:  # Ensure we only handle up to 4 TPs and TP is not empty
                                                        message = f"TRADE MADE BY COUNTER\nFrom: {group_name}\ntrade_type: {trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nDate: {message_date_str}"
                                                        if placeOrder(symbol, trade_type, sl, tp, price, magic_number):
                                                            send_telegram_message(JDBCopyTrading_chat_id, message)
                                                        else:
                                                            print("Failed to place order")
                                                
                                                #This wil place the Trade under JDB Copy Trading Counter
                                                for i, tp in enumerate(tps):
                                                    if i < 4 and tp:  # Ensure we only handle up to 4 TPs and TP is not empty
                                                        message = f"TRADE MADE BY COUNTER\nFrom: {group_name}\ntrade_type: {trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nDate: {message_date_str}"
                                                        if placeOrder(symbol, trade_type, sl, tp, price, groups_info.get('JDB Copy Trading Counter')):
                                                            send_telegram_message(JDBCopyTrading_chat_id, message)
                                                        else:
                                                            print("Failed to place order")
                                            else:
                                                for i, tp in enumerate(tps):    
                                                    if i < 4 and tp:  # Ensure we only handle up to 4 TPs and TP is not empty
                                                        message = f"Actual TRADE OUTSIDE OF COUNTER\nFrom: {group_name}\ntrade_type: {trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nDate: {message_date_str}"
                                                        if placeOrder(symbol, trade_type, sl, tp, price, magic_number):
                                                            send_telegram_message(JDBCopyTrading_chat_id, message)
                                                        else:
                                                            print("Failed to place order")
                                                       
                                except IndexError:
                                    print(f"Error parsing message from {group_name}: {message_text}")
                                except Exception as e:
                                    print(f"Unexpected error: {e}")

                            await parse_and_send_messages(message_text)

                            last_message_ids[group_name] = latest_message.id

        except Exception as e:
            print(f"Error processing group messages: {e}")

        # Wait for 10 seconds before checking again
        await asyncio.sleep(10)

#Telegram Groups


def InitializeAccounts():
    print("----------InitializeAccounts---------")
    
   
    
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

    # Start date to filter messages
    start_date = datetime.now(timezone.utc)
    

    async with aiohttp.ClientSession() as session:
        await process_all_group_messages(start_date, session)

with client:
    client.loop.run_until_complete(main())
