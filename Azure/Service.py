import asyncio
import datetime
import json
import socket
import threading
import time
import uuid
import MetaTrader5 as mt5
import os
import sqlite3

from datetime import datetime

ADDRESS = "127.0.0.1"
PORT = 9094

sent_trades = set()

clients = set()
client_accounts = {}

dbPath = ""

def print_to_console_and_file(message):
    with open("C:/Temp/output.txt", "a") as outputfile:
        print(message, file=outputfile)
    print(message)

class AccountList:
    def __init__(self, accountList_Number, accountList_Name):
        self.accountList_Number = accountList_Number
        self.accountList_Name = accountList_Name

def AddCommunication(accountNumber, message):
    DB_CONNECTION = dbPath
    db_conn = sqlite3.connect(DB_CONNECTION)
    db_cursor = db_conn.cursor()
    db_cursor.execute("INSERT INTO tbl_Communication (tbl_Communication_AccountNumber, tbl_Communication_Message) VALUES (?, ?)", (accountNumber, message))
    db_conn.commit()
    db_conn.close()

async def RequestHandler(json_string, writer):
    try:
        json_data = json.loads(json_string)

        action = json_data.get('Code')

        if action == "TradeStatus":
            TradeStatus(json_data)
        elif action == "TradeProfit":
            TradeProfit(json_data)
        elif action == "Authenticate":
            await ClientConnected(writer, json_data)  # Ensure to await async function
        else:
            print("Invalid action code.")
    
    except json.JSONDecodeError:
        return "Invalid JSON string."

def TradeStatus(json_data):
    print("TradeStatus")
    print(json_data)

def TradeProfit(json_data):
    print("TradeProfit")
    print(json_data)

async def ClientConnected(writer, json_data):
    try:
        account_id = json_data.get('account_id')
        if account_id:
            client_accounts[writer] = account_id

        broadcast_message = json.dumps({"status": "broadcast", "data": json_data})
        await broadcast(broadcast_message)  # Ensure to await async function

        print_connected_clients()
    except json.JSONDecodeError:
        print("Received data is not valid JSON")

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')

    clients.add(writer)

    try:
        while True:
            data = await reader.read(2048)
            if data:
                json_received = data.decode('utf-8')
                await RequestHandler(json_received, writer)  # Ensure to await async function
            else:
                break
    except asyncio.CancelledError:
        pass
    except ConnectionResetError:
        print(f"Client {addr} forcibly closed the connection")
    except OSError as e:
        print(f"OSError for client {addr}: {e}")
    finally:
        print(f"Client {addr} disconnected")
        clients.remove(writer)
        if writer in client_accounts:
            del client_accounts[writer]
            print(client_accounts.values())
        writer.close()

        try:
            await writer.wait_closed()
        except ConnectionResetError:
            pass  
        except OSError:
            pass 

async def broadcast(message):
    for client in clients:
        client.write(message.encode('utf-8'))
        await client.drain()

def print_connected_clients():
    if client_accounts:
        print(client_accounts.values())
    else:
        print("No connected clients")

def check_for_new_trades(loop):
    print("Checking for opened trades")

    while True:
        current_time = datetime.now()

        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        trades = mt5.positions_get()
        if trades is None:
            print("No trades found or error in fetching trades.")
        elif trades:
            for trade in trades:
                if trade.ticket not in sent_trades:
                    sent_trades.add(trade.ticket)

                    DB_CONNECTION = dbPath
                    db_conn = sqlite3.connect(DB_CONNECTION)
                    db_cursor = db_conn.cursor()
                    db_cursor.execute("INSERT INTO tbl_ActiveTrade (tbl_ActiveTrade_TicketNr) VALUES (?)", (trade.ticket,))
                    db_conn.commit()
                    db_conn.close()

                    trade_details = {
                        "Code": "OpenTrade",
                        "Symbol": trade.symbol,
                        "Ticket": trade.ticket,
                        "Time": trade.time,
                        "Time Update": trade.time_update,
                        "Type": trade.type,
                        "Magic": trade.magic,
                        "Identifier": trade.identifier,
                        "Reason": trade.reason,
                        "Volume": trade.volume,
                        "Open Price": trade.price_open,
                        "SL": trade.sl,
                        "TP": trade.tp,
                        "Current Price": trade.price_current,
                        "Swap": trade.swap,
                        "Profit": trade.profit,
                        "Comment": trade.comment,
                        "External ID": trade.external_id
                    }
                    trade_details_json = json.dumps(trade_details)
                    print(trade_details_json)
                    asyncio.run_coroutine_threadsafe(broadcast(trade_details_json), loop)
        
        time.sleep(1)  # Add a sleep to avoid high CPU usage

def is_position_closed(account, position_ticket):
    positions = account.positions_get()
    for position in positions:
        if position.ticket == position_ticket:
            return False
    return True

def closeTradeOnAllAccounts(ticket):
    trade_details = {
        "Code": "CloseTrade",
        "Ticket": ticket
    }

    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    trade_details_json = json.dumps(trade_details)
    print(trade_details_json)

def check_for_closed_trades():
    print("Checking for closed trades")

    while True:
        current_time = datetime.now()
        # Format the date and time
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
        # select all trades from tbl_ActiveTrade
        DB_CONNECTION = dbPath
        db_conn = sqlite3.connect(DB_CONNECTION)
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT tbl_ActiveTrade_TicketNr FROM tbl_ActiveTrade")
        trades_listArray = []
        for row in db_cursor.fetchall():
            trades_listArray.append(row[0])
        
        # check if trade still in mt5 if not delete from tbl_ActiveTrade
        for trade in trades_listArray:
            if is_position_closed(mt5, trade):
                closeTradeOnAllAccounts(trade)
                db_cursor.execute("DELETE FROM tbl_ActiveTrade WHERE tbl_ActiveTrade_TicketNr = ?", (trade,))
                db_conn.commit()

        db_conn.close()
        time.sleep(1)  # Add a sleep to avoid high CPU usage

def InitializeAccounts():
    print_to_console_and_file("----------InitializeAccounts---------")
    
    DB_CONNECTION = dbPath
    
    db_conn = sqlite3.connect(DB_CONNECTION)

    db_cursor = db_conn.cursor()

    # get main account
    db_cursor.execute("SELECT tbl_account_id, tbl_account_password, tbl_account_server, tbl_account_name FROM tbl_account WHERE tbl_account_active = 1 AND tbl_account_mainaccount = 1")
    counter = 0
    for row in db_cursor.fetchall():
        counter = counter + 1
        # MAIN
        instance_path = os.path.join(DIRECTORY, "Instances", str(counter), "terminal64.exe")

        if not mt5.initialize(login=int(row[0]), password=row[1], server=row[2], path=instance_path):
            print("Failed to initialize MT5 terminal from", instance_path)
            print("Error:", mt5.last_error())
        else:
            print("MT5 initialized successfully for account ID:", row[0])
            accountList = AccountList(mt5, "MainAccount")
            account_List.append(accountList)

    db_cursor.execute("SELECT tbl_ActiveTrade_TicketNr FROM tbl_ActiveTrade")
    for row in db_cursor.fetchall():
        sent_trades.add(row[0])

    db_conn.close()

async def main_async():
    server = await asyncio.start_server(handle_client, ADDRESS, PORT)
    print(f"Server listening on {ADDRESS}:{PORT}")
    async with server:
        await server.serve_forever()

def main():
    InitializeAccounts()

    loop = asyncio.get_event_loop()

    check_open_trade_thread = threading.Thread(target=check_for_new_trades, args=(loop,))
    check_open_trade_thread.start()

    check_close_trade_thread = threading.Thread(target=check_for_closed_trades)
    check_close_trade_thread.start()

    loop.run_until_complete(main_async())

    print("\n =====ALL SERVICES STARTED====== \n")

if __name__ == "__main__":
    account_List = []

    PATH = os.path.abspath(__file__)
    DIRECTORY = os.path.dirname(os.path.dirname(PATH))
    dbPath = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

    main()
