import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sqlite3
import os

PATH = os.path.abspath(__file__)
DIRECTORY = os.path.dirname(os.path.dirname(PATH))
db_path = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

# Initialize Database Connection
def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_user
                 (pk_tbl_user INTEGER PRIMARY KEY AUTOINCREMENT,
                  tbl_user_name TEXT NOT NULL,
                  tbl_user_email TEXT NOT NULL,
                  tbl_user_AccountNumber INTEGER NOT NULL,
                  tbl_user_IDNumber INTEGER NOT NULL,
                  tbl_user_Active INTEGER NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_Account
                 (pk_tbl_account INTEGER PRIMARY KEY AUTOINCREMENT,
                  tbl_account_name TEXT NOT NULL,
                  tbl_account_id TEXT NOT NULL,
                  tbl_account_password TEXT NOT NULL,
                  tbl_account_server TEXT NOT NULL,
                  tbl_account_active INTEGER NOT NULL,
                  tbl_account_mainaccount INTEGER NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_ActiveTrade
                 (tbl_ActiveTrade_TicketNr INTEGER NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_trade
                 (pk_tbl_trade INTEGER PRIMARY KEY AUTOINCREMENT,
                  tbl_trade_account INTEGER NOT NULL,
                  tbl_trade_ticket TEXT NOT NULL,
                  tbl_trade_magic TEXT NOT NULL,
                  tbl_trade_volume REAL NOT NULL,
                  tbl_trade_profit REAL NOT NULL,
                  tbl_trade_symbol TEXT NOT NULL,
                  tbl_trade_billed INTEGER NOT NULL,
                  tbl_trade_time TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_Communication
                 (pk_tbl_Communication INTEGER PRIMARY KEY AUTOINCREMENT,
                  tbl_Communication_AccountNumber INTEGER NOT NULL,
                  tbl_Communication_Time TEXT NOT NULL,
                  tbl_Communication_Message TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_Transactions
                 (pk_tbl_Transactions INTEGER PRIMARY KEY AUTOINCREMENT,
                  tbl_Transactions_AccountNumber INTEGER NOT NULL,
                  tbl_Transactions_DateFrom TEXT NOT NULL,
                  tbl_Transactions_DateTo TEXT NOT NULL,
                  tbl_Transactions_TradeCount INTEGER NOT NULL,
                  tbl_Transactions_Profit REAL NOT NULL,
                  tbl_Transactions_Paid BOOLEAN NOT NULL DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_TradeTransaction
                 (pk_tbl_TradeTransaction INTEGER PRIMARY KEY AUTOINCREMENT,
                  fk_tbl_Transactions INTEGER NOT NULL,
                  fk_tbl_trade INTEGER NOT NULL,
                  FOREIGN KEY (fk_tbl_Transactions) REFERENCES tbl_Transactions (pk_tbl_Transactions),
                  FOREIGN KEY (fk_tbl_trade) REFERENCES tbl_trade (pk_tbl_trade))''')
    
    conn.commit()
    conn.close()

# Generic Functions for CRUD operations
def insert_record(table, entries, checkboxes=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        columns = list(entries.keys())
        values = [entry.get() for entry in entries.values()]

        if checkboxes:
            for col, var in checkboxes.items():
                columns.append(col)
                values.append(var.get())

        placeholders = ', '.join(['?' for _ in values])
        columns_str = ', '.join(columns)
        query = f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders})'
        c.execute(query, values)
        conn.commit()
        clear_entries(entries, checkboxes)
        display_records(table, treeviews[table])
    except Exception as e:
        messagebox.showerror("Insert Error", f"Failed to insert record: {e}")
    finally:
        conn.close()

def update_record(table, entries, pk, checkboxes=None):
    selected_item = treeviews[table].selection()[0]
    values = treeviews[table].item(selected_item, 'values')
    pk_value = values[0]  # Assuming the primary key is the first column in the treeview

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        set_clause = ', '.join([f'{col} = ?' for col in entries.keys()])
        values = [entry.get() for entry in entries.values()]

        if checkboxes:
            for col, var in checkboxes.items():
                set_clause += f', {col} = ?'
                values.append(var.get())

        values.append(pk_value)
        query = f'UPDATE {table} SET {set_clause} WHERE {pk} = ?'
        c.execute(query, values)
        conn.commit()
        clear_entries(entries, checkboxes)
        display_records(table, treeviews[table])
    except Exception as e:
        messagebox.showerror("Update Error", f"Failed to update record: {e}")
    finally:
        conn.close()

def delete_record(table, pk):
    selected_item = treeviews[table].selection()[0]
    values = treeviews[table].item(selected_item, 'values')
    pk_value = values[0]  # Assuming the primary key is the first column in the treeview

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        query = f'DELETE FROM {table} WHERE {pk} = ?'
        c.execute(query, (pk_value,))
        conn.commit()
        treeviews[table].delete(selected_item)
    except Exception as e:
        messagebox.showerror("Delete Error", f"Failed to delete record: {e}")
    finally:
        conn.close()

def display_records(table, tree, query=None, params=()):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        if query is None:
            c.execute(f'SELECT * FROM {table}')
        else:
            c.execute(query, params)
        records = c.fetchall()
        for row in tree.get_children():
            tree.delete(row)
        for record in records:
            tree.insert("", "end", values=record)
    except Exception as e:
        messagebox.showerror("Display Error", f"Failed to display records: {e}")
    finally:
        conn.close()

def clear_entries(entries, checkboxes=None):
    for entry in entries.values():
        entry.delete(0, tk.END)
    if checkboxes:
        for var in checkboxes.values():
            var.set(0)

def on_tree_select(event, table, entries, checkboxes=None):
    selected_item = treeviews[table].selection()[0]
    values = treeviews[table].item(selected_item, 'values')

    for (col, entry), value in zip(entries.items(), values[1:]):
        entry.delete(0, tk.END)
        entry.insert(0, value)

    if checkboxes:
        offset = len(entries) + 1  # Adjust for primary key
        for (col, var), value in zip(checkboxes.items(), values[offset:]):
            var.set(value)

# Function to sort columns
def sort_column(tree, col, reverse):
    items = [(tree.set(k, col), k) for k in tree.get_children('')]
    items.sort(reverse=reverse)

    for index, (val, k) in enumerate(items):
        tree.move(k, '', index)

    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

# Function to handle search in tbl_trade and tbl_Communication
def search_records(table, entries):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        columns = list(entries.keys())
        values = [entry.get() for entry in entries.values()]
        
        query = f"SELECT * FROM {table} WHERE " + " AND ".join([f"{col} LIKE ?" for col in columns])
        params = [f"%{value}%" for value in values]
        
        display_records(table, treeviews[table], query, params)
    except Exception as e:
        messagebox.showerror("Search Error", f"Failed to search records: {e}")
    finally:
        conn.close()

# Initialize GUI
init_db()
root = tk.Tk()
root.title("SQLite DB Manager")

# Create Notebook for Tabs
notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, sticky="nsew")

# Create frames for each tab
tables = {
    'tbl_Account': ('pk_tbl_account', {
        'tbl_account_name': 'Name',
        'tbl_account_id': 'Account ID',
        'tbl_account_password': 'Password',
        'tbl_account_server': 'Server',
        'tbl_account_active': 'Active',
        'tbl_account_mainaccount': 'Main Account'
    }),
    'tbl_user': ('pk_tbl_user', {
        'tbl_user_name': 'Name',
        'tbl_user_email': 'Email',
        'tbl_user_AccountNumber': 'Account Number',
        'tbl_user_IDNumber': 'ID Number',
        'tbl_user_Active': 'Active'
    }),
    'tbl_trade': ('pk_tbl_trade', {
        'tbl_trade_account': 'Account',
        'tbl_trade_ticket': 'Ticket',
        'tbl_trade_magic': 'Magic',
        'tbl_trade_volume': 'Volume',
        'tbl_trade_profit': 'Profit',
        'tbl_trade_symbol': 'Symbol',
        'tbl_trade_billed': 'Billed',
        'tbl_trade_time': 'Time'
    }),
    'tbl_Communication': ('pk_tbl_Communication', {
        'tbl_Communication_AccountNumber': 'Account Number',
        'tbl_Communication_Time': 'Time',
        'tbl_Communication_Message': 'Message'
    }),
    'tbl_ActiveTrade': ('tbl_ActiveTrade_TicketNr', {
        'tbl_ActiveTrade_TicketNr': 'Ticket Number'
    }),
    'tbl_Transactions': ('pk_tbl_Transactions', {
        'tbl_Transactions_AccountNumber': 'Account Number',
        'tbl_Transactions_DateFrom': 'Date From',
        'tbl_Transactions_DateTo': 'Date To',
        'tbl_Transactions_TradeCount': 'Trade Count',
        'tbl_Transactions_Profit': 'Profit',
        'tbl_Transactions_Paid': 'Paid'
    })
}

# Tab Names
tab_names = {
    'tbl_Account': 'Account',
    'tbl_user': 'Copy Trade Users',
    'tbl_trade': 'All Trades',
    'tbl_Communication': 'Communication',
    'tbl_ActiveTrade': 'Active Trades',
    'tbl_Transactions': 'Trade Summary'
}

treeviews = {}
for table, (pk, columns) in tables.items():
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=tab_names[table])

    # Labels and Entries
    entries = {}
    checkboxes = {}
    row_offset = 0
    for i, (col, text) in enumerate(columns.items()):
        ttk.Label(frame, text=text).grid(row=i + row_offset, column=0, padx=5, pady=5, sticky=tk.W)
        
        if col in ['tbl_account_active', 'tbl_account_mainaccount', 'tbl_user_Active', 'tbl_Transactions_Paid']:
            var = tk.IntVar()
            checkbox = ttk.Checkbutton(frame, variable=var)
            checkbox.grid(row=i + row_offset, column=1, padx=5, pady=5)
            checkboxes[col] = var
        else:
            entry = ttk.Entry(frame)
            entry.grid(row=i + row_offset, column=1, padx=5, pady=5)
            entries[col] = entry

    if table == 'tbl_user':
        # Update and Delete functionality for tbl_user
        ttk.Button(frame, text="Update", command=lambda tbl=table, ent=entries, pk=pk, cb=checkboxes: update_record(tbl, ent, pk, cb)).grid(row=len(columns), column=0, padx=5, pady=5)
        ttk.Button(frame, text="Delete", command=lambda tbl=table, pk=pk: delete_record(tbl, pk)).grid(row=len(columns), column=1, padx=5, pady=5)
        
        # Add a button under the grid for additional functionality
        ttk.Button(frame, text="Run Trades For The Week", command=lambda: RunTradeForTheWeek()).grid(row=len(columns) + 2, column=0, padx=5, pady=5)
        # Your code here

    elif table == 'tbl_trade' or table == 'tbl_Communication':
        # Search functionality for tbl_trade and tbl_Communication
        ttk.Button(frame, text="Search", command=lambda tbl=table, ent=entries: search_records(tbl, ent)).grid(row=len(columns), column=0, padx=5, pady=5)
    else:
        # Insert, Update, Delete, and Clear buttons for other tables
        ttk.Button(frame, text="Insert", command=lambda tbl=table, ent=entries, cb=checkboxes: insert_record(tbl, ent, cb)).grid(row=len(columns), column=0, padx=5, pady=5)
        ttk.Button(frame, text="Update", command=lambda tbl=table, ent=entries, pk=pk, cb=checkboxes: update_record(tbl, ent, pk, cb)).grid(row=len(columns), column=1, padx=5, pady=5)
        ttk.Button(frame, text="Delete", command=lambda tbl=table, pk=pk: delete_record(tbl, pk)).grid(row=len(columns), column=2, padx=5, pady=5)
        ttk.Button(frame, text="Clear", command=lambda ent=entries, cb=checkboxes: clear_entries(ent, cb)).grid(row=len(columns), column=3, padx=5, pady=5)
    
    # Refresh button
    ttk.Button(frame, text="Refresh", command=lambda tbl=table: display_records(tbl, treeviews[tbl])).grid(row=len(columns), column=4, padx=5, pady=5)

    # Treeview
    cols = [pk] + list(columns.keys())
    tree = ttk.Treeview(frame, columns=cols, show='headings')
    for col in cols:
        tree.heading(col, text=col, command=lambda _col=col: sort_column(tree, _col, False))
    tree.grid(row=len(columns) + 1, column=0, columnspan=5, padx=5, pady=5)
    tree.bind("<ButtonRelease-1>", lambda event, tbl=table, ent=entries, cb=checkboxes: on_tree_select(event, tbl, ent, cb))

    treeviews[table] = tree
    display_records(table, tree)

# Add "Filter on Account" tab
filter_frame = ttk.Frame(notebook)
notebook.add(filter_frame, text="Filter on Account")

# Search fields for tbl_account
ttk.Label(filter_frame, text="Account Name").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
account_name_entry = ttk.Entry(filter_frame)
account_name_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(filter_frame, text="Account ID").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
account_id_entry = ttk.Entry(filter_frame)
account_id_entry.grid(row=0, column=3, padx=5, pady=5)

# Search fields for tbl_user
ttk.Label(filter_frame, text="User Name").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
user_name_entry = ttk.Entry(filter_frame)
user_name_entry.grid(row=0, column=5, padx=5, pady=5)

ttk.Label(filter_frame, text="User Email").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
user_email_entry = ttk.Entry(filter_frame)
user_email_entry.grid(row=0, column=7, padx=5, pady=5)

# Search buttons
ttk.Button(filter_frame, text="Search Account", command=lambda: search_accounts()).grid(row=0, column=8, padx=5, pady=5)
ttk.Button(filter_frame, text="Search User", command=lambda: search_users()).grid(row=0, column=9, padx=5, pady=5)

# Treeview for tbl_account
account_tree = ttk.Treeview(filter_frame, columns=["tbl_account_name", "tbl_account_id"], show='headings')
account_tree.heading("tbl_account_name", text="Account Name", command=lambda: sort_column(account_tree, "tbl_account_name", False))
account_tree.heading("tbl_account_id", text="Account ID", command=lambda: sort_column(account_tree, "tbl_account_id", False))
account_tree.grid(row=1, column=0, columnspan=5, padx=5, pady=5)
account_tree.bind("<ButtonRelease-1>", lambda event: handle_selection(event, "account"))

# Treeview for tbl_user
user_tree = ttk.Treeview(filter_frame, columns=["tbl_user_name", "tbl_user_email", "tbl_user_AccountNumber"], show='headings')
user_tree.heading("tbl_user_name", text="User Name", command=lambda: sort_column(user_tree, "tbl_user_name", False))
user_tree.heading("tbl_user_email", text="User Email", command=lambda: sort_column(user_tree, "tbl_user_email", False))
user_tree.heading("tbl_user_AccountNumber", text="Account Number", command=lambda: sort_column(user_tree, "tbl_user_AccountNumber", False))
user_tree.grid(row=1, column=5, columnspan=5, padx=5, pady=5)
user_tree.bind("<ButtonRelease-1>", lambda event: handle_selection(event, "user"))

# Treeview for tbl_trade
trade_tree = ttk.Treeview(filter_frame, columns=["pk_tbl_trade", "tbl_trade_account", "tbl_trade_ticket", "tbl_trade_magic", "tbl_trade_volume", "tbl_trade_profit", "tbl_trade_symbol", "tbl_trade_billed", "tbl_trade_time"], show='headings')
for col in ["pk_tbl_trade", "tbl_trade_account", "tbl_trade_ticket", "tbl_trade_magic", "tbl_trade_volume", "tbl_trade_profit", "tbl_trade_symbol", "tbl_trade_billed", "tbl_trade_time"]:
    trade_tree.heading(col, text=col, command=lambda _col=col: sort_column(trade_tree, _col, False))
trade_tree.grid(row=2, column=0, columnspan=10, padx=5, pady=5)

# Treeview for tbl_Communication
communication_tree = ttk.Treeview(filter_frame, columns=["pk_tbl_Communication", "tbl_Communication_AccountNumber", "tbl_Communication_Time", "tbl_Communication_Message"], show='headings')
for col in ["pk_tbl_Communication", "tbl_Communication_AccountNumber", "tbl_Communication_Time", "tbl_Communication_Message"]:
    communication_tree.heading(col, text=col, command=lambda _col=col: sort_column(communication_tree, _col, False))
communication_tree.grid(row=3, column=0, columnspan=10, padx=5, pady=5)

# Refresh button for Filter on Account tab
ttk.Button(filter_frame, text="Refresh", command=lambda: [search_accounts(), search_users()]).grid(row=4, column=0, columnspan=10, padx=5, pady=5)

def search_accounts():
    query = "SELECT tbl_account_name, tbl_account_id FROM tbl_Account"
    params = []
    if account_name_entry.get() or account_id_entry.get():
        query += " WHERE 1=1"
        if account_name_entry.get():
            query += " AND tbl_account_name LIKE ?"
            params.append(f"%{account_name_entry.get()}%")
        if account_id_entry.get():
            query += " AND tbl_account_id LIKE ?"
            params.append(f"%{account_id_entry.get()}%")
    display_records('tbl_Account', account_tree, query, params)

def search_users():
    query = "SELECT tbl_user_name, tbl_user_email, tbl_user_AccountNumber FROM tbl_user"
    params = []
    if user_name_entry.get() or user_email_entry.get():
        query += " WHERE 1=1"
        if user_name_entry.get():
            query += " AND tbl_user_name LIKE ?"
            params.append(f"%{user_name_entry.get()}%")
        if user_email_entry.get():
            query += " AND tbl_user_email LIKE ?"
            params.append(f"%{user_email_entry.get()}%")
    display_records('tbl_user', user_tree, query, params)

def handle_selection(event, source):
    if source == "account":
        user_tree.selection_remove(user_tree.selection())
        filter_related_records("account")
    elif source == "user":
        account_tree.selection_remove(account_tree.selection())
        filter_related_records("user")

def filter_related_records(source):
    if source == "account":
        selected_item = account_tree.selection()[0]
        values = account_tree.item(selected_item, 'values')
        account_id = values[1]

        # Filter tbl_trade records
        trade_query = "SELECT * FROM tbl_trade WHERE tbl_trade_account = ?"
        display_records('tbl_trade', trade_tree, trade_query, (account_id,))

        # Filter tbl_Communication records
        communication_query = "SELECT * FROM tbl_Communication WHERE tbl_Communication_AccountNumber = ?"
        display_records('tbl_Communication', communication_tree, communication_query, (account_id,))
    elif source == "user":
        selected_item = user_tree.selection()[0]
        values = user_tree.item(selected_item, 'values')
        user_account_number = values[2]  # Assuming the third column is the account number

        # Filter tbl_trade records
        trade_query = "SELECT * FROM tbl_trade WHERE tbl_trade_account = ?"
        display_records('tbl_trade', trade_tree, trade_query, (user_account_number,))

        # Filter tbl_Communication records
        communication_query = "SELECT * FROM tbl_Communication WHERE tbl_Communication_AccountNumber = ?"
        display_records('tbl_Communication', communication_tree, communication_query, (user_account_number,))

def RunTradeForTheWeek():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        # Calculate the summary and insert/update into tbl_Transactions
        c.execute('''
            WITH DateRange AS (
                SELECT
                    DATE('now', 'weekday 0', '-7 days') AS start_date,
                    DATE('now') AS end_date
            ),
            UnallocatedTrades AS (
                SELECT
                    tbl_trade_account AS account_number,
                    COUNT(*) AS total_trades,
                    SUM(tbl_trade_profit) AS total_profit
                FROM
                    tbl_trade
                WHERE
                    DATE(tbl_trade_time) BETWEEN (SELECT start_date FROM DateRange) AND (SELECT end_date FROM DateRange)
                    AND pk_tbl_trade NOT IN (SELECT fk_tbl_trade FROM tbl_TradeTransaction)
                GROUP BY
                    tbl_trade_account
            )
            INSERT INTO tbl_Transactions (
                tbl_Transactions_AccountNumber,
                tbl_Transactions_DateFrom,
                tbl_Transactions_DateTo,
                tbl_Transactions_TradeCount,
                tbl_Transactions_Profit,
                tbl_Transactions_Paid
            )
            SELECT
                account_number,
                (SELECT start_date FROM DateRange) AS start_date,
                (SELECT end_date FROM DateRange) AS end_date,
                total_trades,
                total_profit,
                0
            FROM
                UnallocatedTrades
            WHERE
                NOT EXISTS (
                    SELECT 1 FROM tbl_Transactions
                    WHERE tbl_Transactions.tbl_Transactions_AccountNumber = UnallocatedTrades.account_number
                    AND tbl_Transactions.tbl_Transactions_DateFrom = (SELECT start_date FROM DateRange)
                    AND tbl_Transactions.tbl_Transactions_DateTo = (SELECT end_date FROM DateRange)
                )
        ''')

        # Get the last inserted summary IDs for each account
        summary_ids = c.execute('''
            SELECT pk_tbl_Transactions, tbl_Transactions_AccountNumber
            FROM tbl_Transactions
            WHERE tbl_Transactions_DateFrom = (SELECT DATE('now', 'weekday 0', '-7 days'))
            AND tbl_Transactions_DateTo = DATE('now')
        ''').fetchall()

        # Insert records into tbl_TradeTransaction for each account
        for summary_id, account_number in summary_ids:
            c.execute('''
                INSERT INTO tbl_TradeTransaction (
                    fk_tbl_Transactions,
                    fk_tbl_trade
                )
                SELECT
                    ? AS fk_tbl_Transactions,
                    pk_tbl_trade
                FROM
                    tbl_trade
                WHERE
                    tbl_trade_account = ?
                    AND DATE(tbl_trade_time) BETWEEN DATE('now', 'weekday 0', '-7 days') AND DATE('now')
                    AND pk_tbl_trade NOT IN (SELECT fk_tbl_trade FROM tbl_TradeTransaction)
            ''', (summary_id, account_number))

        # Update tbl_user by setting tbl_user_Active to 0 for users with the same tbl_user_AccountNumber as tbl_Transactions_AccountNumber
        c.executemany('''
            UPDATE tbl_user
            SET tbl_user_Active = 0
            WHERE tbl_user_AccountNumber = ?
        ''', [(account_number,) for _, account_number in summary_ids])

        conn.commit()
        messagebox.showinfo("Success", "Trade summary for the week has been calculated and inserted successfully.")
    except Exception as e:
        messagebox.showerror("RunTradeForTheWeek Error", f"Failed to run trade summary for the week: {e}")
    finally:
        conn.close()

def update_paid_status(transaction_id, paid_status):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE tbl_Transactions
            SET tbl_Transactions_Paid = ?
            WHERE pk_tbl_Transactions = ?
        ''', (paid_status, transaction_id))

        if paid_status:
            c.execute('''
                UPDATE tbl_user
                SET tbl_user_Active = 1
                WHERE tbl_user_AccountNumber = (
                    SELECT tbl_Transactions_AccountNumber
                    FROM tbl_Transactions
                    WHERE pk_tbl_Transactions = ?
                )
            ''', (transaction_id,))
        
        conn.commit()
    except Exception as e:
        messagebox.showerror("Update Paid Status Error", f"Failed to update paid status: {e}")
    finally:
        conn.close()

# Display all accounts and users initially
search_accounts()
search_users()

root.mainloop()
