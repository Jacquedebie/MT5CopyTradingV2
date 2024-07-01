import asyncio
import json
from database_handler import insert_trade

async def monitor_mt5(queue):
    print("Monitoring MT5 for new trades...")

    #sign into accounts
    #loop for new trades
    #put new trades into queue


    while True:

        await asyncio.sleep(5) 

        new_trade = {
            "Code": "NewTrade",
            "trade_id": 12345,
            "details": "Trade details here"
        }

        await queue.put(json.dumps(new_trade))
        await insert_trade(new_trade['trade_id'], new_trade['details'])
