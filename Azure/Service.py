import asyncio
import datetime
import json
import threading
import time
import MetaTrader5 as mt5
import os
import sqlite3

import Meta1 as  mt5_Client_1

import subprocess

from datetime import datetime , timedelta

#ADDRESS = "127.0.0.1"
ADDRESS = "0.0.0.0"
PORT = 9094

sent_trades = set()

clients = set()
client_accounts = {}

dbPath = ""

trailing_stop_distance = 1

#----------------  Websocket Server  ----------------

async def RequestHandler(json_string, writer):
    
    client_id = client_accounts.get(writer, "")
    
    AddCommunication(client_id, json_string)

    try:
        json_data = json.loads(json_string)

        action = json_data.get('Code')

        if action == "TradeStatus":
            TradeStatus(json_data)
        elif action == "TradeProfit":
            TradeProfit(client_id,json_data)
        elif action == "Authenticate":
            await ClientConnected(writer, json_data)  # Ensure to await async function
        elif action == "Ping":
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            #print(f"[{current_time}] ping received")
        else:
            print("Invalid action code.")
    
    except json.JSONDecodeError:
        return "Invalid JSON string."

def TradeStatus(json_data):
    print(json_data)

def TradeProfit(client_id,json_data):
    InsertTrade(client_id,json_data)

async def ClientConnected(writer, json_data):
    try:
        account_id = json_data.get('AccountId')
        user_Email = json_data.get('Email')
        user_Name = json_data.get('Name')
        user_Id = json_data.get('IdentificationNumber')

        if account_id:
            client_accounts[writer] = account_id
            AddCommunication(client_accounts.get(writer, ""),"Conected")

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            DB_CONNECTION = dbPath
            db_conn = sqlite3.connect(DB_CONNECTION)
            db_cursor = db_conn.cursor()
            db_cursor.execute("SELECT tbl_user_Active FROM tbl_user WHERE tbl_user_accountNumber = ?", (account_id,))

            rows = db_cursor.fetchall()
            number_of_rows = len(rows)

            if(number_of_rows > 0):
                print("Account already exist")
            else:
                db_cursor.execute("INSERT INTO tbl_user (tbl_user_name, tbl_user_email, tbl_user_accountNumber, tbl_user_idnumber, tbl_user_Active) VALUES (?,?,?,?,?)", (user_Name,user_Email,account_id,user_Id,1))
                db_conn.commit()

            db_conn.close()
            
        except sqlite3.Error as error:
            print("Error occurred:", error)

        print(f"[{current_time}] Client Connected :")
        print( client_accounts.values())


    except json.JSONDecodeError:
        print("Received data is not valid JSON")

async def handle_client(reader, writer):

    addr = writer.get_extra_info('peername')

    clients.add(writer)

    authenticateRequest = {"Code": "Authenticate"}

    writer.write(json.dumps(authenticateRequest).encode('utf-8'))

    try:
        while True:
            data = await reader.read(2048)
            if data:
                json_received = data.decode('utf-8')
                
                await RequestHandler(json_received, writer)  
            else:
                break
    except asyncio.CancelledError:
        pass
    except ConnectionResetError:
        print(f"Client {addr} forcibly closed the connection")
    except OSError as e:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] OSError for client {addr}: {e}")
    finally:
        print(f"Client {addr} disconnected")
        AddCommunication(client_accounts.get(writer, ""),"Disconect")

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

    AddCommunication(str(list(client_accounts.values())), message)

async def DirectBroadcast(client,message):
    

    client.write(message.encode('utf-8'))
    await client.drain()

    AddCommunication(client, message)

#----------------  MT5 Listener  ----------------

class AccountList:
    def __init__(self, accountList_Number, accountList_Name):
        self.accountList_Number = accountList_Number
        self.accountList_Name = accountList_Name

def check_for_new_trades(loop):
    print("Checking for opened trades")

    while True:
        current_time = datetime.now()

        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        tradesa = mt5.positions_get()
        tradesb = mt5_Client_1.positions_get()

        if tradesa:
            for trade in tradesa:
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
                    asyncio.run_coroutine_threadsafe(broadcast(trade_details_json), loop)
                    
        if tradesb is None:
            print("No trades found or error in fetching trades.")
        elif tradesb:
            for trade in tradesb:
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
                    asyncio.run_coroutine_threadsafe(broadcast(trade_details_json), loop)
        
        time.sleep(1)  # Add a sleep to avoid high CPU usage

def check_for_modify_trades(loop):
    print("Checking for Modify trades")

    while True:
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
        trades = mt5_Client_1.positions_get()
        for tradeMt5 in trades:
            symbol_info = mt5_Client_1.symbol_info(tradeMt5.symbol)
            price = symbol_info.ask
            #print(f"Profit from Trade {tradeMt5.ticket}: {tradeMt5.profit}")
            if tradeMt5.profit > 0:
                #print(f"Trade {tradeMt5.ticket} is in profit. Modifying stop loss")
                current_stop_loss = tradeMt5.sl
                new_stop_loss = price - trailing_stop_distance if tradeMt5.type == mt5_Client_1.ORDER_TYPE_BUY else price + trailing_stop_distance
                #print(f"Current stop loss: {current_stop_loss}, New stop loss: {new_stop_loss}")
                #if (tradeMt5.type == mt5.ORDER_TYPE_BUY and new_stop_loss > current_stop_loss) or (tradeMt5.type == mt5.ORDER_TYPE_SELL and new_stop_loss < current_stop_loss):
                if (tradeMt5.type == mt5.ORDER_TYPE_BUY and new_stop_loss > current_stop_loss and new_stop_loss > tradeMt5.price_open) or (tradeMt5.type == mt5.ORDER_TYPE_SELL and new_stop_loss < current_stop_loss and new_stop_loss < tradeMt5.price_open):
                    modify_position(mt5_Client_1,tradeMt5.ticket, tradeMt5.symbol, new_stop_loss)

        time.sleep(1)  

def modify_position(account,order_number, symbol, new_stop_loss):
    # Create the request
    request = {
        "action": mt5_Client_1.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "sl": new_stop_loss,
        "position": order_number
    }
    # Send order to MT5
    order_result = account.order_send(request)
    if order_result[0] == 10009:
        return True
    else:
        print_to_console_and_file("modify_position account Last MT5 Error : " + order_result.comment)
        return False

def check_for_closed_trades(loop):
    print("Checking for closed trades")

    while True:
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
        DB_CONNECTION = dbPath
        db_conn = sqlite3.connect(DB_CONNECTION)
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT tbl_ActiveTrade_TicketNr FROM tbl_ActiveTrade")
        trades_listArray = [row[0] for row in db_cursor.fetchall()]
        
        for trade in trades_listArray:
            if is_position_closed(trade):
                trade_details = {
                                    "Code": "CloseTrade",
                                    "Ticket": trade
                                }

                trade_details_json = json.dumps(trade_details)

                asyncio.run_coroutine_threadsafe(broadcast(trade_details_json), loop)
                db_cursor.execute("DELETE FROM tbl_ActiveTrade WHERE tbl_ActiveTrade_TicketNr = ?", (trade,))
                db_conn.commit()

        db_conn.close()
        time.sleep(1)  

def is_position_closed(position_ticket):
    positions = mt5.positions_get()
    for position in positions:
        if position.ticket == position_ticket:
            return False

    positions = mt5_Client_1.positions_get()
    for position in positions:
        if position.ticket == position_ticket:
            return False

    return True

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
        instance_path = os.path.join(DIRECTORY, "Instances", str(1), "terminal64.exe")

        if not mt5.initialize(login=int(row[0]), password=row[1], server=row[2], path=instance_path):
            print("Failed to initialize MT5 terminal from", instance_path)
            print("Error:", mt5.last_error())
        else:
            print("MT5 initialized successfully for account ID:", row[0])
            accountList = AccountList(mt5, "MainAccount")
            account_List.append(accountList)

    db_cursor.execute("SELECT tbl_account_id, tbl_account_password, tbl_account_server, tbl_account_name FROM tbl_account WHERE tbl_account_active = 1 AND tbl_account_mainaccount = 0")
    counter = 0
    for row in db_cursor.fetchall():
        counter = counter + 1
        # MAIN
        instance_path = os.path.join(DIRECTORY, "Instances", str(2), "terminal64.exe")

        if not mt5_Client_1.initialize(login=int(row[0]), password=row[1], server=row[2], path=instance_path):
            print("Failed to initialize MT5 terminal from", instance_path)
            print("Error:", mt5.last_error())
        else:
            print("MT5 initialized successfully for account ID:", row[0])
            accountList = AccountList(mt5_Client_1, "Account2")
            account_List.append(accountList)


    db_cursor.execute("SELECT tbl_ActiveTrade_TicketNr FROM tbl_ActiveTrade")
    for row in db_cursor.fetchall():
        sent_trades.add(row[0])

    db_conn.close()

def GetTradeDetails(loop):
    while True:
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now() + timedelta(days=1)
        for account in account_List:
            
            trades = account.accountList_Number.history_deals_get(from_date, to_date)
            if trades is None:
                print(f"No trade history for account {account['login']}, error code: {mt5.last_error()}")
            else:
                account_info = account.accountList_Number.account_info()
                InsertTradeDetail(account_info.login, trades)
                
    
        time.sleep(6000)  
#----------------  DB & Files  ----------------

def print_to_console_and_file(message):
    with open("C:/Temp/output.txt", "a") as outputfile:
        print(message, file=outputfile)
    print(message)

def AddCommunication(accountNumber, message):

    date = datetime.now()

    DB_CONNECTION = dbPath
    db_conn = sqlite3.connect(DB_CONNECTION)
    db_cursor = db_conn.cursor()
    db_cursor.execute("INSERT INTO tbl_Communication (tbl_Communication_AccountNumber,tbl_Communication_Time, tbl_Communication_Message) VALUES (?, ?, ?)", (accountNumber, date,message))
    db_conn.commit()
    db_conn.close()

def InsertTrade(client_id,trade_data):
   
    print(trade_data)

    # Extracting the necessary fields from the JSON
    trade_ticket = trade_data.get('Ticket')
    trade_magic = trade_data.get('MagicNumber')
    trade_volume = float(trade_data.get('Volume', 0))
    trade_profit = float(trade_data.get('Profit', 0))
    trade_symbol = trade_data.get('Symbol')
    trade_time = trade_data.get('OrderTime')

    DB_CONNECTION = dbPath
    db_conn = sqlite3.connect(DB_CONNECTION)
    db_cursor = db_conn.cursor()
    
    db_cursor.execute("""
        INSERT INTO tbl_trade (
            tbl_trade_account,
            tbl_trade_ticket, 
            tbl_trade_magic, 
            tbl_trade_volume, 
            tbl_trade_profit, 
            tbl_trade_symbol,
            tbl_trade_billed,
            tbl_trade_time
        ) VALUES (?,?, ?, ?, ?, ?, ?,?)""", 
        (client_id,trade_ticket, trade_magic, trade_volume, trade_profit, trade_symbol,0,trade_time)
    )
    
    db_conn.commit()
    db_conn.close()

def InsertTradeDetail(accountNumber,trade_data):
    DB_CONNECTION = dbPath
    db_conn = sqlite3.connect(DB_CONNECTION)
    db_cursor = db_conn.cursor()
    
    for trade in trade_data:
        trade_ticket = str(trade.ticket)

        db_cursor.execute("SELECT tbl_trade_ticket FROM tbl_trade WHERE tbl_trade_ticket = ?", (trade_ticket,))
        deal = db_cursor.fetchone()

        if deal is None:
            trade_dataJason = {
                            "Ticket": trade.ticket,
                            "MagicNumber": trade.magic,
                            "Volume": trade.volume,
                            "Profit": trade.profit,
                            "Symbol": trade.symbol,
                            "OrderTime": datetime.fromtimestamp(trade.time).strftime('%Y-%m-%d %H:%M:%S')
                        }
            InsertTrade(accountNumber,trade_dataJason)
    
    db_conn.close()

#----------------  Main Loops  ----------------

async def main_async():
    server = await asyncio.start_server(handle_client, ADDRESS, PORT)
    print(f"Server listening on {ADDRESS}:{PORT}")
    async with server:
        await server.serve_forever()

def main():
    InitializeAccounts()

    # script_path = os.path.dirname(os.path.abspath(__file__)) + '\ReadTelegramGroup.py'
    
    # # Run the script
    # result = subprocess.run(['python', script_path], capture_output=True, text=True)

    # # Print the output of the script
    # print("resutls : " + result.stdout)

    loop = asyncio.get_event_loop()

    check_open_trade_thread = threading.Thread(target=check_for_new_trades, args=(loop,))
    check_open_trade_thread.start()

    check_close_trade_thread = threading.Thread(target=check_for_closed_trades, args=(loop,))
    check_close_trade_thread.start()

    check_modify_trade_thread = threading.Thread(target=check_for_modify_trades, args=(loop,))
    check_modify_trade_thread.start()

    check_TradeDetail_thread = threading.Thread(target=GetTradeDetails, args=(loop,))
    check_TradeDetail_thread.start()

    loop.run_until_complete(main_async())

    print("\n =====ALL SERVICES STARTED====== \n")

if __name__ == "__main__":
    account_List = []

    PATH = os.path.abspath(__file__)
    DIRECTORY = os.path.dirname(os.path.dirname(PATH))
    dbPath = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

    # def run_script(script_path):
    #     subprocess.run(['python', script_path])

    # # Path to the other script
    # script_path = os.path.dirname(os.path.abspath(__file__)) + '\ReadTelegramGroup.py'

    # # Create a thread to run the script
    # script_thread = threading.Thread(target=run_script, args=(script_path,))

    # # Start the thread
    # script_thread.start()

    # # Continue with the main program
    # print('The script is running in a separate thread.')

    # # Optional: Wait for the thread to finish if needed
    # script_thread.join()

    # Path to the script
    script_path = os.path.dirname(os.path.abspath(__file__)) + '\ReadTelegramGroup.py'

    # Command to open a new command prompt and run the script
    subprocess.Popen(['start', 'cmd', '/k', f'python {script_path}'], shell=True)

    main()

