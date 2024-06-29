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

ClientSockets = {}

sent_trades = set()

dbPath = ""

def print_to_console_and_file(message):
    with open("C:/Temp/output.txt", "a") as outputfile:
        print(message, file=outputfile)  
    print(message)  

class AccountList:
    def __init__(self, accountList_Number,accountList_Name):
        self.accountList_Number = accountList_Number
        self.accountList_Name = accountList_Name

def AddCommunication(accountNumber, message):
    DB_CONNECTION = dbPath
    db_conn = sqlite3.connect(DB_CONNECTION)
    db_cursor = db_conn.cursor()
    db_cursor.execute("INSERT INTO tbl_Communication (tbl_Communication_AccountNumber,tbl_Communication_Message) VALUES (?,?)", (accountNumber,message))
    db_conn.commit()
    db_conn.close()

def RequestHandler(client_id,client_socket,json_string):

    AddCommunication(client_id,json_string)

    try:
        json_data = json.loads(json_string)

        action = json_data.get('Code')

        if action == "TradeStatus":
            TradeStatus(json_data)
        elif action == "TradeProfit":
            TradeProfit(json_data)
        elif action == "ClientConnected":
            ClientConnected(json_data,client_socket)
        else:
            print("Invalid action code.")
    
    except json.JSONDecodeError:
        return "Invalid JSON string."

def TradeStatus(json_data):
    print("TradeStatus")
    print(json_data)

def TradeProfit(json_data):

    print(json_data)

def ClientConnected(json_data,client_socket):

    print(json_data)

    client_id = json_data.get('ClientID')

    existing_client_id = None

    for id, socket in ClientSockets.items():
        if socket == client_socket:
            existing_client_id = id
            break

    if existing_client_id:
        del ClientSockets[existing_client_id]
    

    #Confirm if the client is allowed to connect to the server
    #If allowed, add the client to the list of connected clients


    ClientSockets[client_id] = client_socket
    
    print(f"Connected clients: {ClientSockets}")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ADDRESS, PORT))
    server_socket.listen(5)

    print(f"Server listening on {ADDRESS}:{PORT} \n")

    return server_socket

def handle_client_connection(client_socket):

    try:
        while True:

            request = client_socket.recv(1024)

            if not request:
                print("Connection closed by the client")
                break

    except Exception as e:

        print(f"Error handling client connection: {e}")

    finally:

        try:

            for key, value in list(ClientSockets.items()):
                if value == client_socket:
                    del ClientSockets[key]
                    break

            client_socket.close()

        except Exception as e:

            print(f"Error closing client socket: {e}")

def listen_for_connections(server_socket):
    print("Checking for incoming connections")

    while True:
        client_socket, addr = server_socket.accept()
        
        ClientSockets[str(uuid.uuid4())] = client_socket

        # Send a message to the client to confirm connection and get the client's details
        trade_details = {
                        "Code": "Authenticate"
                        }
        
        trade_details_json = json.dumps(trade_details)

        client_socket.send(trade_details_json.encode('utf-8'))

        client_handler = threading.Thread(target=handle_client_connection, args=(client_socket,))
        client_handler.start()

def listen_for_messages():
    
    print("Checking for incoming messages from clients")
    
    while True:
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        for client_id, client_socket in list(ClientSockets.items()):
            try:

                message = client_socket.recv(1024)

                if message:
                    RequestHandler(client_id,client_socket,message.decode('utf-8'))
                else:

                    for key, value in list(ClientSockets.items()):
                        if value == client_socket:
                            del ClientSockets[key]
                            break

                    client_socket.close()
                        
                    print("Client disconnected.")

            except Exception as e:

                print(f"Error receiving message from client: {e}")

                try:
                    for key, value in list(ClientSockets.items()):
                        if value == client_socket:
                            del ClientSockets[key]
                            break

                    client_socket.close()

                except Exception as e:
                    print(f"Error closing client socket: {e}")

def check_for_new_trades():
    
    print("Checking for opened trades")

    while True:
        current_time = datetime.now()

        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        trades = mt5.positions_get()
        if trades:
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
                        "Symbol": trade.symbol,
                        "Comment": trade.comment,
                        "External ID": trade.external_id
                    }
                    trade_details_json = json.dumps(trade_details)

                    send_message_to_all_clients(trade_details_json)

def is_position_closed(account,position_ticket):
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
    
    send_message_to_all_clients(trade_details_json)

def check_for_closed_trades():
    print('Close Trade')
    while True:
        current_time = datetime.now()
        # Format the date and time
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
        #time.sleep(1)
        #select all trades from tbl_ActiveTrade
        DB_CONNECTION = dbPath
        db_conn = sqlite3.connect(DB_CONNECTION)
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT tbl_ActiveTrade_TicketNr FROM tbl_ActiveTrade")
        trades_listArray = []
        for row in db_cursor.fetchall():
            trades_listArray.append(row[0])
        
        #check if trade still in mt5 if not delete from tbl_ActiveTrade
        for trade in trades_listArray:
            if is_position_closed(mt5,trade):
                
                closeTradeOnAllAccounts(trade)

                db_cursor.execute("DELETE FROM tbl_ActiveTrade WHERE tbl_ActiveTrade_TicketNr = ?", (trade,))
                db_conn.commit()

        db_conn.close()

def InitializeAccounts():
    print_to_console_and_file("----------InitializeAccounts---------")
    
    DB_CONNECTION = dbPath
    
    db_conn = sqlite3.connect(DB_CONNECTION)

    db_cursor = db_conn.cursor()

    #get main account
    db_cursor.execute("SELECT tbl_account_id,tbl_account_password,tbl_account_server,tbl_account_name FROM tbl_account WHERE tbl_account_active = 1 AND tbl_account_mainaccount = 1")
    counter = 0
    for row in db_cursor.fetchall():
        counter = counter + 1
        #MAIN
        instance_path = os.path.join(DIRECTORY, "Instances", str(counter), "terminal64.exe")

        if not mt5.initialize(login=int(row[0]), password=row[1], server=row[2], path=instance_path):
            print("Failed to initialize MT5 terminal from", instance_path)
            print("Error:", mt5.last_error())
        else:
            print("MT5 initialized successfully for account ID:", row[0])
            accountList = AccountList(mt5,"MainAccount")
            account_List.append(accountList)

    db_cursor.execute("SELECT tbl_ActiveTrade_TicketNr FROM tbl_ActiveTrade")
    for row in db_cursor.fetchall():
        sent_trades.add(row[0])

    db_conn.close()

def send_message_to_all_clients(message):

    for client_id, client_socket in list(ClientSockets.items()):
        try:
            client_socket.send(message.encode('utf-8'))
            AddCommunication(client_id,message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message to client {client_id}: {e}")

            for key, value in list(ClientSockets.items()):
                if value == client_socket:
                    del ClientSockets[key]
                    break

            client_socket.close()

def main():
    InitializeAccounts();

    server_socket = start_server()

    listener_thread = threading.Thread(target=listen_for_connections, args=(server_socket,))
    listener_thread.start()

    message_listener_thread = threading.Thread(target=listen_for_messages)
    message_listener_thread.start()

    check_open_trade_thread = threading.Thread(target=check_for_new_trades)
    check_open_trade_thread.start()

    check_close_trade_thread = threading.Thread(target=check_for_closed_trades)
    check_close_trade_thread.start()

    # Add similar threads for check_for_closed_trades() if needed

    print("\n =====ALL SERVICES STARTED====== \n")

if __name__ == "__main__":
    account_List = []

    PATH = os.path.abspath(__file__)
    #DIRECTORY = os.path.dirname(PATH)
    DIRECTORY = os.path.dirname(os.path.dirname(PATH))
    dbPath = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

    main()
