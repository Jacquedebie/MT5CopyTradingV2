import pandas as pd
import sqlite3
import os

# Define the absolute path to the file
file_path = r'C:\Users\Janco.Weyers\Desktop\MT5CopyTradingV2\DataBases\AllTelegramGroups.xlsx'
db_path = r'C:\Users\Janco.Weyers\Desktop\MT5CopyTradingV2\DataBases\CopyTradingV2.db'

# Load the Excel file
df = pd.read_excel(file_path)

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if the table exists and create it if it doesn't
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tbl_telegramGroups (
        pk_tbl_telegramGroups INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_telegramGroups_GroupName TEXT UNIQUE,
        tbl_telegramGroup_MagicNumber INTEGER UNIQUE,
        tbl_telegramGroup_ActiveIndicator INTEGER,
        tbl_telegramGroup_DeactiveReason TEXT
    )
""")

# Iterate through the DataFrame and insert or update data in the database
for index, row in df.iterrows():
    # Check if the group name or magic number already exists in the database
    cursor.execute("SELECT pk_tbl_telegramGroups FROM tbl_telegramGroups WHERE tbl_telegramGroups_GroupName = ? OR tbl_telegramGroup_MagicNumber = ?", 
                   (row['tbl_telegramGroups_GroupName'], row['tbl_telegramGroup_MagicNumber']))
    result = cursor.fetchone()
    
    if result is None:
        # If not found, insert the row into the database
        cursor.execute("""
            INSERT INTO tbl_telegramGroups (
                pk_tbl_telegramGroups,
                tbl_telegramGroups_GroupName,
                tbl_telegramGroup_MagicNumber,
                tbl_telegramGroup_ActiveIndicator,
                tbl_telegramGroup_DeactiveReason
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            row['pk_tbl_telegramGroups'],
            row['tbl_telegramGroups_GroupName'],
            row['tbl_telegramGroup_MagicNumber'],
            row['tbl_telegramGroup_ActiveIndicator'],
            row.get('tbl_telegramGroup_DeactiveReason', None)  # Handle missing values
        ))
    else:
        # If found, update the status and deactive reason
        cursor.execute("""
            UPDATE tbl_telegramGroups
            SET tbl_telegramGroup_ActiveIndicator = ?,
                tbl_telegramGroup_DeactiveReason = ?
            WHERE pk_tbl_telegramGroups = ?
        """, (
            row['tbl_telegramGroup_ActiveIndicator'],
            row.get('tbl_telegramGroup_DeactiveReason', None),  # Handle missing values
            result[0]  # Use the primary key from the SELECT result to update the correct row
        ))

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Data imported and updated successfully!")
