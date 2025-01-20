import re
import json
from telethon import TelegramClient, events
import MetaTrader5 as mt5
import os

# Define your API ID, API Hash, and phone number
api_id = '21789309'
api_hash = '25cfde9a425a3658172d011e45e81a2c'
phone = '+2784583071'

# MT5 Login Credentials
mt5_account = 52007136
mt5_password = "ZlqgA03fF&m$az"
mt5_server = "ICMarketsSC-Demo"

# List of groups to monitor
groups_to_monitor = ["JDB Copy Signals", "GHP 🦁 VIP-JACKPOT 🇳🇱 FX"]

# File to store trade details
trade_file = "trade_data.json"

# Create the Telegram client
client = TelegramClient('session_name', api_id, api_hash, connection_retries=None, timeout=30)

def print_to_console_and_file(message):
    # Get the current working directory
    current_directory = os.getcwd()
    
    # Define the output file path
    output_file_path = os.path.join(current_directory, "TelegramOutputV3.txt")
    
    # Append the message to the file and print to the console
    with open(output_file_path, "a", encoding="utf-8") as outputfile:
        outputfile.write(f"{message}\n")  # Write the message to the file
    print(message)  # Print the message to the console


# Connect to MetaTrader 5
def connect_to_mt5():
    if not mt5.initialize():
        print_to_console_and_file(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return False
    if not mt5.login(mt5_account, password=mt5_password, server=mt5_server):
        print_to_console_and_file(f"❌ MT5 login failed: {mt5.last_error()}")
        return False
    print_to_console_and_file("✅ Connected to MT5")
    return True

def extract_tp_and_sl(message_text):
    # Debugging: Print raw message text
    #print(f"Raw message text: {repr(message_text)}")

    # Extract SL
    sl_match = re.search(r"[^\w]*SL\s*[: ]\s*(\d+\.?\d*)", message_text, re.IGNORECASE)
    stop_loss = float(sl_match.group(1)) if sl_match else None
    if stop_loss:
        print_to_console_and_file(f"✅ Extracted SL: {stop_loss}")
    else:
        print_to_console_and_file("❌ SL not found in the message text.")

    # Extract TP levels
    tp_matches = re.findall(r"[^\w]*TP\d*\s*[: ]\s*(\d+\.?\d*)", message_text, re.IGNORECASE)

    #tp_matches = re.findall(r"T[Pp]\d*[: ]\s*(\d+\.?\d*)", message_text, re.IGNORECASE)
    if tp_matches:
        print_to_console_and_file(f"✅ Extracted TP levels: {tp_matches}")
    else:
        print_to_console_and_file("❌ TP levels not found in the message text.")

    return stop_loss, [float(tp) for tp in tp_matches]

# Save trade details to a file
def save_trade(message_id, magic_number):
    try:
        with open(trade_file, 'r') as file:
            trades = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        trades = {}

    trades[str(message_id)] = magic_number

    with open(trade_file, 'w') as file:
        json.dump(trades, file, indent=4)

# Check if a message ID exists in the file
def check_trade(message_id):
    try:
        with open(trade_file, 'r') as file:
            trades = json.load(file)
            return trades.get(str(message_id))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Function to extract the trading pair
def extract_pair(message_text):
    # Explicit list of trading pairs to match
    pair_match = re.search(r"\b(GOLD|BTCUSD|XAUUSD|XAGUSD|USOIL|UKOIL|[A-Z]{3,6}USD)\b", message_text, re.IGNORECASE)
    if pair_match:
        trading_pair = pair_match.group(1).upper()

        # Map GOLD to XAUUSD
        if trading_pair == "GOLD":
            trading_pair = "XAUUSD"

        print_to_console_and_file(f"Extracted trading pair: {trading_pair}")
        return trading_pair

    print_to_console_and_file("No trading pair found.")
    return None


# Function to extract entry value from the message
def extract_entry_value(message_text):
    range_match = re.search(r"Entry.*?(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", message_text, re.IGNORECASE)
    single_match = re.search(r"Entry.*?(\d+\.?\d*)", message_text, re.IGNORECASE)

    if range_match:
        last_number = range_match.group(2)
        print_to_console_and_file(f"Extracted last number from Entry range: {last_number}")
        return float(last_number)
    elif single_match:
        entry_value = single_match.group(1)
        print_to_console_and_file(f"Extracted single Entry value: {entry_value}")
        return float(entry_value)
    print_to_console_and_file("No valid Entry line found.")
    return None

# Function to determine order type
def determine_order_type(trading_pair, entry_price, trade_type, margin_threshold=50):
    symbol_info = mt5.symbol_info(trading_pair)
    if not symbol_info:
        print_to_console_and_file(f"❌ Symbol {trading_pair} not found in MT5.")
        return None

    market_price = symbol_info.bid if trade_type == "SELL" else symbol_info.ask
    print_to_console_and_file(f"Current market price for {trading_pair}: {market_price}")

    if trade_type == "SELL":
        if entry_price < market_price:
            return "SELL MARKET"
        else:
            return "SELL LIMIT"

    if trade_type == "BUY":
        if entry_price > market_price:
            return "BUY MARKET"
        else:
            return "BUY LIMIT"

    print_to_console_and_file(f"❌ Could not determine order type for trade type: {trade_type}")
    return None

# Function to place a trade
def place_trade(symbol, entry_price, sl, tp, trade_type, lot_size=0.1, magic_number=None, group_name=None):
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        print_to_console_and_file(f"❌ Symbol {symbol} not found in MT5.")
        return False

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print_to_console_and_file(f"❌ Failed to select symbol {symbol} for trading.")
            return False

    order_type_map = {
        "BUY MARKET": mt5.ORDER_TYPE_BUY,
        "SELL MARKET": mt5.ORDER_TYPE_SELL,
        "BUY LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
        "SELL LIMIT": mt5.ORDER_TYPE_SELL_LIMIT
    }
    order_type = order_type_map.get(trade_type)
    if not order_type:
        print_to_console_and_file(f"❌ Invalid trade type: {trade_type}")
        return False

    # Modify comment_text based on group_name
    if group_name == "GHP 🦁 VIP-JACKPOT 🇳🇱 FX":
        comment_text = "GoldHunter VIP"
    else:
        comment_text = f"Group: {group_name}" if group_name else "Trade placed via Python script"


    request = {
        "action": mt5.TRADE_ACTION_PENDING if "LIMIT" in trade_type else mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": symbol_info.volume_min,
        "type": order_type,
        "price": entry_price if "LIMIT" in trade_type else None,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": magic_number,
        "comment": comment_text,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    if "MARKET" in trade_type:
        del request["price"]

    print_to_console_and_file(f"Trade request: {request}")

    result = mt5.order_send(request)
    if result is None:
        print_to_console_and_file(f"❌ mt5.order_send failed: {mt5.last_error()}")
        return False

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print_to_console_and_file(f"✅ Trade placed successfully: {result}")
        return True
    else:
        print_to_console_and_file(f"❌ Failed to place trade: {result}")
        return False

# Remove a trade from the file
def remove_trade_from_file(message_id):
    try:
        with open(trade_file, 'r') as file:
            trades = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print_to_console_and_file("Trade file not found or invalid.")
        return

    trades.pop(str(message_id), None)

    with open(trade_file, 'w') as file:
        json.dump(trades, file, indent=4)
    print_to_console_and_file(f"✅ Removed trade with message ID {message_id} from the file.")

# Close all trades for a given magic number
def close_all_trades(magic_number):
    """
    Closes all active trades and cancels pending orders in MT5 associated with the given magic number.
    """
    # Close active positions
    positions = mt5.positions_get()
    if positions is None:
        print_to_console_and_file(f"❌ Failed to retrieve positions: {mt5.last_error()}")
        return False

    closed_all = True
    for position in positions:
        if position.magic == magic_number:
            trade_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            close_price = mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": trade_type,
                "position": position.ticket,
                "price": close_price,
                "deviation": 10,
                "magic": position.magic,
                "comment": "Closed via Telegram signal",
                "type_filling": mt5.ORDER_FILLING_IOC
            }

            print_to_console_and_file(f"Attempting to close position {position.ticket} with magic number {position.magic}")
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                print_to_console_and_file(f"❌ Failed to close trade {position.ticket}: {result}")
                closed_all = False
            else:
                print_to_console_and_file(f"✅ Successfully closed trade {position.ticket}")

    # Cancel pending orders
    orders = mt5.orders_get()
    if orders is None:
        print_to_console_and_file(f"❌ Failed to retrieve orders: {mt5.last_error()}")
        return False

    for order in orders:
        if order.magic == magic_number:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket,
                "symbol": order.symbol,
                "magic": order.magic,
                "comment": "Canceled via Telegram signal"
            }

            print_to_console_and_file(f"Attempting to cancel order {order.ticket} with magic number {order.magic}")
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                print_to_console_and_file(f"❌ Failed to cancel order {order.ticket}: {result}")
                closed_all = False
            else:
                print_to_console_and_file(f"✅ Successfully canceled order {order.ticket}")

    return closed_all

def set_break_even(magic_number):
    """
    Sets the Stop Loss (SL) to the entry price for all trades with the given magic number.
    """
    positions = mt5.positions_get()
    if positions is None:
        print_to_console_and_file(f"❌ Failed to retrieve positions: {mt5.last_error()}")
        return False

    updated_all = True
    for position in positions:
        if position.magic == magic_number:
            # Update SL to entry price
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "symbol": position.symbol,
                "sl": position.price_open,  # Set SL to entry price
                "tp": position.tp,  # Keep TP unchanged
                "magic": position.magic,
                "comment": "Break-even update"
            }

            print_to_console_and_file(f"Setting SL to break-even for position {position.ticket} (Entry: {position.price_open})")
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                print_to_console_and_file(f"❌ Failed to update SL for trade {position.ticket}: {result}")
                updated_all = False
            else:
                print_to_console_and_file(f"✅ Successfully updated SL to break-even for trade {position.ticket}")
    return updated_all

def delete_all_limit_trades(magic_number):
    """
    Deletes all pending limit orders for a given magic number.
    """
    orders = mt5.orders_get()
    if orders is None:
        print_to_console_and_file(f"❌ Failed to retrieve orders: {mt5.last_error()}")
        return False

    deleted_all = True
    for order in orders:
        if order.magic == magic_number and (order.type == mt5.ORDER_TYPE_BUY_LIMIT or order.type == mt5.ORDER_TYPE_SELL_LIMIT):
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket,
                "symbol": order.symbol,
                "magic": order.magic,
                "comment": "Canceled via Telegram signal"
            }

            print_to_console_and_file(f"Attempting to cancel order {order.ticket} with magic number {order.magic}")
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                print_to_console_and_file(f"❌ Failed to cancel order {order.ticket}: {result}")
                closed_all = False
            else:
                print_to_console_and_file(f"✅ Successfully canceled order {order.ticket}")

    return deleted_all

def process_message(group_name, message):
    # Extract trading parameters
    trading_pair = extract_pair(message.text)
    entry_value = extract_entry_value(message.text)
    sl, tp_levels = extract_tp_and_sl(message.text)
    trade_type = "BUY" if "BUY" in message.text.upper() else "SELL" if "SELL" in message.text.upper() else None

    print_to_console_and_file("=====================================")
    print_to_console_and_file(f"DEBUG: Extracted values for group {group_name}:")
    print_to_console_and_file(f"  Trading Pair: {trading_pair}")
    print_to_console_and_file(f"  Entry Value: {entry_value}")
    print_to_console_and_file(f"  Stop Loss (SL): {sl}")
    print_to_console_and_file(f"  TP Levels: {tp_levels}")
    print_to_console_and_file(f"  Trade Type: {trade_type}")
    print_to_console_and_file("=====================================")

    if trading_pair and entry_value and trade_type and sl and tp_levels:
        magic_number = message.id  # Use the same magic number for all trades from this signal

        # Determine if the message specifies "1 entry"
        one_entry = "1 entry" in message.text.lower()

        order_type = determine_order_type(trading_pair, entry_value, trade_type)

        if order_type:
            if "LIMIT" in order_type:
                # For LIMIT orders, check if "1 entry" is specified
                if one_entry:
                    # Place only one trade
                    placed = place_trade(
                        symbol=trading_pair,
                        entry_price=entry_value,
                        sl=sl,
                        tp=tp_levels[0] if tp_levels else None,  # Use the first TP
                        trade_type=order_type,
                        lot_size=0.01,
                        magic_number=magic_number,
                        group_name=group_name
                    )
                    if placed:
                        print_to_console_and_file(f"✅ Single trade placed for {trading_pair} at entry price: {entry_value}")
                else:
                    # Place trades progressively closer to SL for all TP levels
                    last_entry_price = entry_value
                    percentage_step = 50  # Define the percentage step (e.g., 20% closer to SL each time)

                    for i, tp in enumerate(tp_levels, start=1):
                        if i > 1:
                            # Calculate the midpoint price based on the percentage step
                            price_difference = abs(last_entry_price - sl)
                            adjustment = price_difference * (percentage_step / 100)
                            midpoint_price = last_entry_price + adjustment if last_entry_price < sl else last_entry_price - adjustment
                            last_entry_price = midpoint_price
                        else:
                            midpoint_price = entry_value

                        placed = place_trade(
                            symbol=trading_pair,
                            entry_price=midpoint_price,
                            sl=sl,
                            tp=tp,
                            trade_type=order_type,
                            lot_size=0.01,
                            magic_number=magic_number,
                            group_name=group_name
                        )
                        if placed:
                            print_to_console_and_file(f"✅ Trade placed for {trading_pair} at entry price: {midpoint_price} (TP{i})")
            else:
                # For MARKET orders, handle "1 entry" condition
                if one_entry:
                    # Place only one trade
                    placed = place_trade(
                        symbol=trading_pair,
                        entry_price=entry_value,
                        sl=sl,
                        tp=tp_levels[0] if tp_levels else None,  # Use the first TP
                        trade_type=order_type,
                        lot_size=0.5,
                        magic_number=magic_number,
                        group_name=group_name
                    )
                    if placed:
                        print_to_console_and_file(f"✅ Single trade placed for {trading_pair} at entry price: {entry_value}")
                else:
                    # Place trades for all TP levels
                    for i, tp in enumerate(tp_levels, start=1):
                        placed = place_trade(
                            symbol=trading_pair,
                            entry_price=entry_value,
                            sl=sl,
                            tp=tp,
                            trade_type=order_type,
                            lot_size=0.5,
                            magic_number=magic_number,
                            group_name=group_name
                        )
                        if placed:
                            print_to_console_and_file(f"✅ Trade placed for {trading_pair} at entry price: {entry_value} (TP{i})")

        save_trade(message.id, magic_number)  # Save the magic number after placing all trades
    else:
        print_to_console_and_file(f"❌ Missing required data to place the trade for group {group_name}.")

def update_trade_sl(magic_number, new_sl):
    """
    Updates the Stop Loss (SL) for all trades associated with the given magic number.
    """
    positions = mt5.positions_get()
    if positions is None:
        print_to_console_and_file(f"❌ Failed to retrieve positions: {mt5.last_error()}")
        return False

    updated_all = True
    for position in positions:
        if position.magic == magic_number:
            # Update the SL for the trade
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "symbol": position.symbol,
                "sl": new_sl,
                "tp": position.tp,  # Keep TP unchanged
                "magic": position.magic,
                "comment": f"SL updated to {new_sl}"
            }

            print_to_console_and_file(f"Updating SL for position {position.ticket} to {new_sl}")
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                print_to_console_and_file(f"❌ Failed to update SL for trade {position.ticket}: {result}")
                updated_all = False
            else:
                print_to_console_and_file(f"✅ Successfully updated SL for trade {position.ticket}")
    return updated_all

@client.on(events.NewMessage)
async def handle_new_message(event):
    chat = await event.get_chat()

    if not hasattr(chat, 'title') or chat.title not in groups_to_monitor:
        return

    group_name = chat.title
    message = event.message
    print_to_console_and_file("==================================================================================================")
    print_to_console_and_file(f"New Message from {group_name}")
    print_to_console_and_file("=====================================")
    print_to_console_and_file(message.text)

    if message.is_reply:
        # Existing logic for handling replies like "close" or "breakeven"
        reply_to_id = message.reply_to_msg_id
        trade_magic = check_trade(reply_to_id)
        if trade_magic:
            print_to_console_and_file(f"Reply is related to a trade with magic number: {trade_magic}")
            if "close" in message.text.lower() or "cancel" in message.text.lower():
                print_to_console_and_file(f"Closing all trades for magic number {trade_magic}.")
                if close_all_trades(trade_magic):
                    remove_trade_from_file(reply_to_id)
                    print_to_console_and_file(f"✅ All trades closed and message ID {reply_to_id} removed.")

            elif "breakeven" in message.text.lower() or "sl to be" in message.text.lower() or "Break Even" in message.text.lower(): #Wait another setup
                print_to_console_and_file(f"Setting SL to break-even for all trades with magic number {trade_magic}.")
                if set_break_even(trade_magic):
                    print_to_console_and_file(f"✅ Successfully set SL to break-even for all trades with magic number {trade_magic}.")
                else:
                    print_to_console_and_file(f"❌ Failed to set SL to break-even for trades with magic number {trade_magic}.")

                # Delete all limit trades specifically for "breakeven"
                print_to_console_and_file(f"Deleting all limit trades for magic number {trade_magic}.")
                if delete_all_limit_trades(trade_magic):
                    print_to_console_and_file(f"✅ Successfully deleted all limit trades for magic number {trade_magic}.")
                else:
                    print_to_console_and_file(f"❌ Failed to delete some limit trades for magic number {trade_magic}.")

            # New "Move SL" command
            elif "move sl" in message.text.lower():
                match = re.search(r"move sl[: ]\s*(\d+\.?\d*)", message.text, re.IGNORECASE)
                if match:
                    new_sl = float(match.group(1))
                    print_to_console_and_file(f"Moving SL to {new_sl} for trades with magic number {trade_magic}.")
                    if update_trade_sl(trade_magic, new_sl):
                        print_to_console_and_file(f"✅ Successfully moved SL to {new_sl} for trades with magic number {trade_magic}.")
                    else:
                        print_to_console_and_file(f"❌ Failed to move SL for trades with magic number {trade_magic}.")

        else:
            print_to_console_and_file("❌ No trade found for the replied message.")
        
        print_to_console_and_file("==================================================================================================")
        return

    process_message(group_name, message)
    print_to_console_and_file("==================================================================================================")

@client.on(events.MessageEdited)
async def handle_edited_message(event):
    chat = await event.get_chat()
    chat_title = chat.title if hasattr(chat, 'title') else None

    if chat_title not in groups_to_monitor:
        return

    message = event.message
    print_to_console_and_file("==================================================================================================")
    print_to_console_and_file(f"Edited Message from {chat_title}")
    print_to_console_and_file("=====================================")
    print_to_console_and_file(message.text)

    # Check if the edited message is related to a trade
    trade_magic = check_trade(message.id)  # Use the message ID as the magic number
    if trade_magic:
        
        print_to_console_and_file(f"Edited message is related to a trade with magic number: {trade_magic}")

        # Close all trades if the message is edited
        print_to_console_and_file(f"Closing all trades for magic number {trade_magic} due to message edit.")
        if close_all_trades(trade_magic):
            remove_trade_from_file(message.id)
            print_to_console_and_file(f"✅ All trades closed and message ID {message.id} removed due to message edit.")
        else:
            print_to_console_and_file(f"❌ Failed to close some trades for magic number {trade_magic}.")

    # Process the edited message
    print_to_console_and_file(f"Processing edited message for group {chat_title}.")
    process_message(chat_title, message)
    print_to_console_and_file("==================================================================================================")


async def main():
    if not connect_to_mt5():
        print_to_console_and_file("Failed to connect to MT5. Exiting.")
        return

    await client.start()
    print_to_console_and_file("Listening for new messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
