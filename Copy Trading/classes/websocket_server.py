import asyncio
import json

HOST = '127.0.0.1'
PORT = 9094

clients = set()
client_accounts = {}

async def RequestHandler(json_string, writer):
    try:
        json_data = json.loads(json_string)
        print(json_data)
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
    print(json_data)

def TradeProfit(json_data):
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
    print(f"Accepted connection from {addr}")
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

async def start_server(queue):
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print(f"Server listening on {HOST}:{PORT}")

    async with server:
        while True:
            message = await queue.get()
            await broadcast(message)
