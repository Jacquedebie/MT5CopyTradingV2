# classes/database_handler.py
import asyncio
import sqlite3


async def insert_trade(trade_id, details):
    print(f"Inserting trade {trade_id} into database...")

async def initialize_database():
    print("Initialising database...")
    await insert_trade(12345, "Trade details here")