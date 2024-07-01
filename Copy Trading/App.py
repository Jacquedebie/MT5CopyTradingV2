import sys
import os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), 'classes'))

from websocket_server import start_server
from mt5_handler import monitor_mt5
from database_handler import initialize_database

async def main():
    
    queue = asyncio.Queue()
    
    await initialize_database()

    await asyncio.gather(
        start_server(queue),
        monitor_mt5(queue)
    )

if __name__ == "__main__":
    asyncio.run(main())
