import MetaTrader5 as mt5
import json
import threading

def check_for_new_trades():
    
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return
    
    if not mt5.login(69885852, "8uNtT$A9WSq$wv3", "XMGlobal-MT5 2"):
        print("Failed to connect to MetaTrader 5")
        return
    
    sent_trades = set()

    while True:
        trades = mt5.positions_get()
        
        if trades:
            for trade in trades:
                if trade.ticket not in sent_trades:
                    sent_trades.add(trade.ticket)
                    trade_details = {
                        "Symbol": trade.symbol,
                        "Type": trade.type,
                        "Volume": trade.volume,
                        "Open Price": trade.price_open,
                        "Ticket": trade.ticket
                    }
                    trade_details_json = json.dumps(trade_details)
                    
                    # Insert code to Send trade details to Azure server

if __name__ == "__main__":
    periodic_message_thread = threading.Thread(target=check_for_new_trades)
    periodic_message_thread.start()
