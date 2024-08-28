import uuid

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

lotSizeToUse = 0.01
preProd = True
takeAllTrades = True

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
symbols = ['XAUUSD', 'GOLD']  # Add more symbols as needed
#'BTCUSD', spread is te hoog
#, 'EURUSD', 'GBPUSD', 'USDJPY', 'EURJPY', 'GBPJPY', 'GBPNZD', 'USOIL', 'USDCAD' Focus net op GOUD

# Dictionary to track counts and timestamps
trade_tracker = {}

save_dir = 'downloaded_images'


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

def placeOrder(symbol, trade_type, sl, tp, price, magic_number,group_name):
    print_to_console_and_file(f"Place order {symbol} {trade_type} TP: {tp} SL: {sl} Price: {price} Magic: {magic_number}")
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print_to_console_and_file(f"Symbol {symbol} not found")
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
        "comment" : group_name
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
                        if latest_message.message is not None:
                            message_text = latest_message.message.upper()  # Convert message to uppercase
                            message_date_str = message_date.strftime('%Y-%m-%d %H:%M:%S')
                            print_to_console_and_file(f'--------------{group_name}-------------------')
                            print_to_console_and_file(f"{group_name}: {message_text} \n{message_date_str}")
                            print_to_console_and_file('---------------------------------')
                            if latest_message.media:
                                #print(f"Attempting to download media: {latest_message.media}")
                                
                                # Create a specific file name using the message ID and add a JPG extension
                                file_name = os.path.join(save_dir, f"{latest_message.id}.jpg")
                                print(f"File Name: {file_name}")
                                try:
                                    print(await latest_message.download_media(file_name))

                                    file_path = await latest_message.download_media(latest_message,thumb=-1, file=file_name)
                                    
                                    if file_path:
                                        print_to_console_and_file(f"Downloaded image to {file_path}")
                                    else:
                                        print_to_console_and_file("Media download failed or returned None.")
                                except Exception as e:
                                    print_to_console_and_file(f"Exception occurred during media download: {str(e)}")
                            else:
                                print_to_console_and_file("No media found in the latest message.")






        except Exception as e:
            print_to_console_and_file(f"Error processing group messages: {e}")

        # Wait for 10 seconds before checking again
        await asyncio.sleep(10)

#Telegram Groups
def populate_telegram_groups():
    global groups_info
    
    

    #groups_info = {"𝐒𝐜𝐚𝐥𝐩𝐞𝐫 𝐋𝐢𝐟𝐞™": "1"}
    #groups_info = {"KT Synthetics": "1"}
    groups_info = {"JDB Copy Signals": "1"}


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
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    await client.start(phone)
    print_to_console_and_file("Client Created")

    # Start date to filter messages
    start_date = datetime.now(timezone.utc)
    
    async with aiohttp.ClientSession() as session:
        await process_all_group_messages(start_date, session)

    await update_task

with client:
    client.loop.run_until_complete(main())
