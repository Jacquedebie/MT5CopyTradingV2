import sqlite3
import os

# Get the absolute path of the current file and determine the directory
PATH = os.path.abspath(__file__)
DIRECTORY = os.path.dirname(os.path.dirname(PATH))
db_path = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# SQL query to select from tbl_trade based on ticket number
select_query = """
SELECT * FROM tbl_trade
WHERE tbl_trade_ticket = ?
"""

# SQL query to update the tbl_trade_drawdown
update_query = """
UPDATE tbl_trade
SET tbl_trade_drawdown = ?
WHERE tbl_trade_ticket = ?
"""

with open('trade_drawdown.txt', 'rb') as file:
    bom = file.read(2)
    if bom == b'\xff\xfe' or bom == b'\xfe\xff':
        file.seek(0)
        text = file.read().decode('utf-16')
    else:
        file.seek(0)
        text = file.read().decode('utf-8')

lines = text.splitlines()

for line in lines:
    line = line.strip()
    if line:  
        values = line.split(',', 1)
        if len(values) == 2:
            ticket_number = values[0].strip()
            max_drawdown = values[1].strip()

            cursor.execute(select_query, (ticket_number,))


            row = cursor.fetchone()

            
            if row:
                print("Row from database:", row)
                print(max_drawdown)
 
                cursor.execute(update_query, (max_drawdown, ticket_number))
                if cursor.rowcount == 0:
                    print(f"Update failed for ticket {ticket_number} with drawdown {max_drawdown}")
                else:
                    print(f"Successfully updated ticket {ticket_number} with drawdown {max_drawdown}")
                conn.commit()  
            else:
                print(f"No row found for ticket {ticket_number}")


conn.close()
