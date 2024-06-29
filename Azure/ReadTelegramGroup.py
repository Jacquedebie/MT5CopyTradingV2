from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import asyncio
import requests
import aiohttp
import time
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

def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
    }
    response = requests.post(url, data=data)

    return response.json()

async def send_http_post_message(session, trade_type, symbol, sl, tp, tp_number):
    print(f"Sending HTTP POST message: {trade_type}, {symbol}, {sl}, {tp}, {tp_number}")
    time.sleep(1)  # Sleep for 1 second to avoid rate limiting
    data = {
        "Code": "Place Trade",
        "Type": trade_type,
        "Symbol": symbol,
        "SL": sl,
        "TP": tp,
        "TP_Number": tp_number
    }
    async with session.post(http_server_url, json=data) as response:
        pass  # Do not wait for the response

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
                    message_text = latest_message.message
                    message_date_str = message_date.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{group_name}: {message_text} at {message_date_str}")

                    def parse_message(text):
                        trade_type = None
                        if "SELL LIMIT" in text:
                            trade_type = "Sell Limit"
                        elif "BUY LIMIT" in text:
                            trade_type = "Buy Limit"
                        elif "SELL" in text:
                            trade_type = "Sell"
                        elif "BUY" in text:
                            trade_type = "Buy"

                        symbol = None
                        if "XAUUSD" in text:
                            symbol = "XAUUSD"
                        elif "GOLD" in text:
                            symbol = "GOLD"

                        sl_line = [line for line in text.split('\n') if 'SL' in line]
                        sl = sl_line[0].split(':')[1].strip() if sl_line else None

                        tp_lines = [line for line in text.split('\n') if 'TP' in line]
                        tps = [line.split(':')[1].strip() for line in tp_lines]

                        return trade_type, symbol, sl, tps

                    async def parse_and_send_messages(message_text):
                        try:
                            trade_type, symbol, sl, tps = parse_message(message_text)

                            if trade_type and symbol and sl and tps:
                                for i, tp in enumerate(tps):
                                    if i < 4:  # Ensure we only handle up to 4 TPs
                                        message = f"{trade_type}\nSymbol: {symbol}\n🚫 SL: {sl}\n💰 TP{i+1}: {tp}\nFrom: {group_name}\nDate: {message_date_str}"
                                        send_telegram_message(JDBCopyTrading_chat_id, message)
                                        asyncio.create_task(send_http_post_message(session, trade_type, symbol, sl, tp, i+1))
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

async def main():
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
