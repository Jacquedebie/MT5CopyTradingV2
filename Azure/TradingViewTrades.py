from flask import Flask, request, jsonify
import MetaTrader5 as mt5

app = Flask(__name__)

def initialize_mt5():
    if not mt5.initialize():
        print(f"Failed to initialize MetaTrader 5, error: {mt5.last_error()}")
        return False
    return True


def get_current_price(symbol):
    """Fetch the current price of a symbol from MT5."""
    symbol_info = mt5.symbol_info_tick(symbol)
    if symbol_info is None:
        print(f"Failed to get price for {symbol}")
        return None
    return symbol_info.ask

def calculate_percentage(symbol_price, percentage=0.10):
    """Calculate a specific percentage of a given symbol price."""
    return symbol_price * (percentage / 100)

def calculate_risk_amount(account_balance, risk_percent=1):
    """Calculate the dollar amount of 1% risk."""
    return account_balance * (risk_percent / 100)

def calculate_lot_size_for_risk(sl_distance, risk_amount, symbol, lot_increment=0.01):
    """Calculate the lot size so that the SL/TP distance results in 1% risk in USD."""
    # Fetch the tick value for the symbol to determine how much 1 pip equals
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Failed to get symbol information for {symbol}")
        return None

    # Calculate the lot size needed so that SL distance corresponds to the risk amount
    initial_lot_size = risk_amount / sl_distance
    lot_size = max(lot_increment, round(initial_lot_size / lot_increment) * lot_increment)
    
    print(f"Initial Calculated Lot Size (before rounding and limits): {initial_lot_size}")
    print(f"Adjusted Lot Size (after applying rounding and limits): {lot_size}")
    return lot_size

def place_order(symbol, order_type, lot_size, sl_price, tp_price):
    """Place an order in MT5."""
    price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
    print(f"Placing {order_type} order for {symbol} at price {price} with SL at {sl_price} and TP at {tp_price}")
    print(f"Final Lot Size for Order: {lot_size}")
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": round(lot_size, 2),  # Rounding lot size for broker compatibility
        "type": order_type,
        "price": float(price),
        "tp": float(tp_price),
        "sl": float(sl_price),
        "deviation": 20,  # Allowing a slight price deviation
        "magic": 1234,
        "type_time": mt5.ORDER_TIME_GTC,  # Good 'til canceled
        "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate or Cancel
        "comment": "JJ's TradingView Order"
    }
    result = mt5.order_send(request)
    return result

def open_trade(symbol, action, volume=1, price=None):
    if not initialize_mt5():
        return

    print(f"Attempting to open trade for {symbol}, action: {action}, volume: {volume}")
    
    if not mt5.symbol_select(symbol, True):
        print(f"Symbol {symbol} not found or not visible in Market Watch.")
        return

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to retrieve tick data for symbol {symbol}.")
        return
    
    print(f"Tick data for {symbol}: Ask={tick.ask}, Bid={tick.bid}")

    tp = 0
    sl = 0
    Factor = 2.675

    if action.lower() == 'buy':
        action_type = mt5.ORDER_TYPE_BUY
        price = price if price else tick.ask
        tp = price + Factor
        sl = price - Factor
    elif action.lower() == 'sell':
        action_type = mt5.ORDER_TYPE_SELL
        price = price if price else tick.bid
        sl = price + Factor
        tp = price - Factor
    else:
        print(f"Invalid action: {action}")
        return

    if price is None or price <= 0:
        print(f"Invalid price detected for {action}: {price}")
        return
    
    print(f"Placing {action} order at price: {price}, TP: {tp}, SL: {sl}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": action_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": "Trade opened via Python",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f"Trade request: {request}")
    
    result = mt5.order_send(request)
    if result is None:
        print("Failed to send trade request, result is None.")
        print(f"MT5 error: {mt5.last_error()}")
        return

    print(f"Trade result: {result}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to execute trade: {result}")
        print(f"MT5 error code: {result.retcode}, description: {mt5.last_error()}")
    else:
        print(f"Trade successful: {result}")


@app.route('/', methods=['POST'])
def root():

    if not initialize_mt5():
        return

    if request.is_json:

        data = request.get_json() 
        print(f"Received data: {data}")

        # open_trade(symbol=data['symbol'], action=data['Action'], volume=2.00)

        symbol = data['symbol']  # Changed to BTCUSD

        # Fetch account balance
        account_info = mt5.account_info()
        account_balance = account_info.balance

        # Fetch current price of the symbol
        current_price = get_current_price(symbol)

        if current_price is not None:
            print(f"Current price of {symbol}: {current_price}")
            
            # Calculate 1% of the account balance for risk management
            risk_amount = calculate_risk_amount(account_balance)
            print(f"Risk Amount (1% of Balance): {risk_amount}")
            
            # Define SL and TP for a Buy order
            percent_value = calculate_percentage(current_price)
            print(f"percent_value {percent_value}")
            if data['Action'].lower() == 'buy':
                action_type = mt5.ORDER_TYPE_BUY
                tp_price = current_price + percent_value
                sl_price = current_price - percent_value
            elif data['Action'].lower() == 'sell':
                action_type = mt5.ORDER_TYPE_SELL
                tp_price = current_price - percent_value
                sl_price = current_price + percent_value
            else:
                print(f"Invalid action: {action}")
                return
            print(f"sl_price: {sl_price} tp_price : {tp_price}" )
            # Calculate SL/TP distance
            sl_distance = int(abs(current_price - sl_price))
            print(f"SL/TP Distance: {sl_distance}")

            # Calculate lot size to ensure 1% risk in USD
            lot_size = calculate_lot_size_for_risk(sl_distance, risk_amount, symbol)
            
            if lot_size is not None:
                print(f"Placing Order: SL = {sl_price}, TP = {tp_price}")
                
                # Place Buy order
                result = place_order(symbol, action_type, lot_size, sl_price, tp_price)
                
                # Print order result
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print(f"Order failed with error: {result.retcode}")
                else:
                    print("Order placed successfully")
        else:
            print(f"Could not fetch the current price for {symbol}")


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
