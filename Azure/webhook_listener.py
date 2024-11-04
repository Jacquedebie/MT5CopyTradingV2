import os
import json
from datetime import datetime, time, timedelta
from flask import Flask, request, jsonify
import MetaTrader5 as mt5

tracking_file = "trade_tracking.json"
app = Flask(__name__)

PATH = os.path.abspath(__file__)
DIRECTORY = os.path.dirname(os.path.dirname(PATH))

def print_to_console_and_file(message):
    # Get the current date in the format YYYY-MM-DD
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"TradingViewData_{date_str}.txt"
    filepath = os.path.join(DIRECTORY, filename)

    # Write to the daily file
    with open(filepath, "a", encoding="utf-8") as outputfile:
        print(message, file=outputfile)  # Print to the file
    print(message)  # Print to the console

def initialize_mt5():
    if not mt5.initialize():
        print_to_console_and_file(f"Failed to initialize MetaTrader 5, error: {mt5.last_error()}")
        return False
    return True

def load_tracking_data():
    """Load tracking data from a JSON file."""
    if not os.path.exists(tracking_file):
        return {}
    with open(tracking_file, "r") as file:
        data = json.load(file)
        print_to_console_and_file(f"Loaded tracking data: {data}")
        return data

def save_tracking_data(data):
    """Save tracking data to a JSON file."""
    print_to_console_and_file(f"Saving tracking data: {data}")
    with open(tracking_file, "w") as file:
        json.dump(data, file)

def reset_tracking_data():
    """Reset tracking data at midnight."""
    current_time = datetime.now().time()
    if time(0, 0) <= current_time <= time(5, 0):  # Between 12 AM and 7 AM
        save_tracking_data({})
        print_to_console_and_file("Tracking data reset.")

def check_trade_conditions(symbol):
    """Check if trading conditions are met for a specific symbol."""
    current_time = datetime.now().time()
    if current_time < time(6, 0):
        print_to_console_and_file(f"Trading is only allowed after 6 AM. Current time: {current_time}")
        return False

    tracking_data = load_tracking_data()
    symbol_data = tracking_data.get(symbol, {'total_trades': 0, 'total_profit_trades': 0, 'stop_trading': 0, 'active_trade_id': None})

    # Check if trading is stopped for this symbol due to a profitable trade or max trades reached
    if symbol_data['stop_trading'] == 1:
        print_to_console_and_file(f"Trading is stopped for {symbol} today due to a profit or max trades reached.")
        return False

    # Check if total trades exceed 2 for the day
    if symbol_data['total_trades'] >= 2:
        print_to_console_and_file(f"Maximum trades (2) reached for {symbol} today. No further trades allowed.")
        return False

    if symbol_data['active_trade_id'] is not None:
        print_to_console_and_file(f"An active trade is already open for {symbol}. No new trade allowed.")
        return False
    return True

def update_tracking_data(symbol, successful_trade, trade_id=None):
    """Update tracking data after a trade for a specific symbol."""
    tracking_data = load_tracking_data()
    symbol_data = tracking_data.get(symbol, {'total_trades': 0, 'total_profit_trades': 0, 'stop_trading': 0, 'active_trade_id': None})

    if successful_trade is not None:
        if symbol_data['total_trades'] < 2:
            symbol_data['total_trades'] += 1

        # Update the active trade ID on a new trade, or clear it if the trade closed
        print_to_console_and_file(f"trade_id {trade_id}")
        symbol_data['active_trade_id'] = trade_id #if not successful_trade else None
        print_to_console_and_file(f"after {symbol_data['active_trade_id']}")
        # If the trade closed in profit, stop further trades for the day for this symbol
        if successful_trade:
            symbol_data['total_profit_trades'] += 1
            symbol_data['stop_trading'] = 1  # Stop further trades if in profit
        else:
            # Allow one more trade if the first was not profitable, else stop
            if symbol_data['total_trades'] >= 2:
                symbol_data['stop_trading'] = 1
            else:
                symbol_data['stop_trading'] = 0

    print_to_console_and_file(f"Updated tracking data for {symbol}: {symbol_data}")
    tracking_data[symbol] = symbol_data
    save_tracking_data(tracking_data)

def is_trade_open(symbol, order_id):
    """
    Check if a trade for a given symbol and order_id is still open.
    """

    # Check open positions for the specified symbol
    open_positions = mt5.positions_get(symbol=symbol)
    if open_positions:
        for position in open_positions:
            if position.ticket == order_id:
                print_to_console_and_file(f"Trade with order ID {order_id} for {symbol} is still open.")
                return True

    # If no matching open position is found, the trade is closed
    print_to_console_and_file(f"Trade with order ID {order_id} for {symbol} is closed.")
    return False

def check_previous_trade_result(symbol):
    """Check if the previous trade for a symbol closed in profit or loss."""
    tracking_data = load_tracking_data()
    symbol_data = tracking_data.get(symbol, {})
    trade_id = symbol_data.get('active_trade_id')
    if trade_id is None:
        return None  # No previous trade to check

    if not is_trade_open(symbol,trade_id):
        start = datetime.now() - timedelta(days=1)
        end = datetime.now() + timedelta(days=1)

        history = mt5.history_deals_get(start, end)
        if history is None:
            print_to_console_and_file(f"Failed to retrieve deal history. Error: {mt5.last_error()}")
            return None
        #print_to_console_and_file(f"All History : {history}")
        for deal in history:
            if deal.position_id == trade_id and deal.entry == 1:
                print_to_console_and_file(f"deal {deal}")
                # Trade closed, clear active trade ID
                symbol_data['active_trade_id'] = None
                tracking_data[symbol] = symbol_data
                save_tracking_data(tracking_data)
                if deal.profit > 0:
                    print_to_console_and_file(f"Previous trade for {symbol} with trade ID {trade_id} closed in profit {deal.profit}.")
                    return True
                else:
                    print_to_console_and_file(f"Previous trade for {symbol} with trade ID {trade_id} did not close in profit {deal.profit}.")
                    return False

    print_to_console_and_file(f"No deal found for trade ID {trade_id} in the last 30 days.")
    return None

def get_current_price(symbol):
    """Fetch the current price of a symbol from MT5."""
    symbol_info = mt5.symbol_info_tick(symbol)
    if symbol_info is None:
        print_to_console_and_file(f"Failed to get price for {symbol}")
        return None
    return symbol_info.ask

def calculate_percentage(symbol_price, percentage=0.10):
    """Calculate a specific percentage of a given symbol price."""
    return symbol_price * (percentage / 100)

def calculate_risk_amount(account_balance, risk_percent=1):
    """Calculate the dollar amount of 1% risk."""
    return account_balance * (risk_percent / 100)

def calculate_lot_size_for_risk(account_balance, symbol, sl_distance,risk_amount):
    
    symbol_info = mt5.symbol_info(symbol)
    
    if symbol_info is None:
        print(f"Failed to retrieve symbol information for {symbol}")
        return None

    print(sl_distance)

    pip_value_per_lot = symbol_info.trade_contract_size * symbol_info.point
    print(f"Pip value per lot: {pip_value_per_lot}")

    lot_size = round((risk_amount / (sl_distance * pip_value_per_lot)) / 100, 2)

    print(f"Calculated lot size: {lot_size}")

    return lot_size

def place_order(symbol, order_type, lot_size, sl_price, tp_price):
    """Place an order in MT5."""
    price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": round(lot_size, 2),
        "type": order_type,
        "price": float(price),
        "tp": float(tp_price),
        "sl": float(sl_price),
        "deviation": 20,
        "magic": 1234,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "comment": "Automated order"
    }
    result = mt5.order_send(request)
    return result

@app.route('/', methods=['POST'])
def root():
    if not initialize_mt5():
        return

    reset_tracking_data()

    if request.is_json:
        data = request.get_json()
        print_to_console_and_file(f"------------------- New Request----------------")
        symbol = data['symbol']
        previous_trade_result = check_previous_trade_result(symbol)
        print_to_console_and_file(f"previous_trade_result {previous_trade_result}")
        if previous_trade_result is False:
            tracking_data = load_tracking_data()
            print_to_console_and_file(f"tracking_data {tracking_data}")
            symbol_data = tracking_data.get(symbol, {'total_trades': 0, 'total_profit_trades': 0, 'stop_trading': 0, 'active_trade_id': None})
            symbol_data['stop_trading'] = 0  # Allow another trade since the previous one was not profitable
            symbol_data['total_profit_trades'] -= 1
            tracking_data[symbol] = symbol_data
            save_tracking_data(tracking_data)

        if not check_trade_conditions(symbol):
            return jsonify({'status': 'error', 'message': f'Trade conditions not met for {symbol}'}), 403

        account_info = mt5.account_info()
        account_balance = account_info.balance
        current_price = get_current_price(symbol)

        if current_price is not None:
            risk_amount = calculate_risk_amount(account_balance)
            percent_value = calculate_percentage(current_price)
            if data['Action'].lower() == 'buy':
                action_type = mt5.ORDER_TYPE_BUY
                tp_price = current_price + percent_value
                sl_price = current_price - percent_value
            elif data['Action'].lower() == 'sell':
                action_type = mt5.ORDER_TYPE_SELL
                tp_price = current_price - percent_value
                sl_price = current_price + percent_value
            else:
                return

            sl_distance = abs(current_price - sl_price)  # Ensure this is a float, not int, for accuracy
            # Calculate lot size directly based on current price and stop-loss price
            lot_size = calculate_lot_size_for_risk(account_balance, symbol, sl_distance,risk_amount)

            if lot_size is not None:
                result = place_order(symbol, action_type, lot_size, sl_price, tp_price)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print_to_console_and_file("Order placed successfully")
                    print_to_console_and_file(f"update_tracking_data {result.order}")
                    update_tracking_data(symbol, successful_trade=True, trade_id=result.order)
                else:
                    print_to_console_and_file(f"Order failed with error: {result.retcode}")
                    update_tracking_data(symbol, successful_trade=None)
        else:
            print_to_console_and_file(f"Could not fetch the current price for {symbol}")

        return jsonify({'status': 'success', 'received': data}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Unsupported Media Type'}), 415

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



#ngrok http 5000  
#https://dashboard.ngrok.com/login
#AffiliateMarketingJDB@gmail.com

#https://dec9-172-174-154-125.ngrok-free.app
# {
#   "symbol": "{{ticker}}",
#   "Action": "sell",
#   "message": "Price alert triggered for {{ticker}} at {{close}}"
# }