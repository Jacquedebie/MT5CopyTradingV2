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
                  tbl_user_IDNumber INTEGER NOT NULL)''')
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
                  tbl_trade_billed INTEGER NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_Communication
                 (pk_tbl_Communication INTEGER PRIMARY KEY AUTOINCREMENT,
                  tbl_Communication_AccountNumber INTEGER NOT NULL,
                  tbl_Communication_Time TEXT NOT NULL,
                  tbl_Communication_Message TEXT NOT NULL)''')
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

# Initialize GUI
init_db()
root = tk.Tk()
root.title("SQLite DB Manager")

# Create Notebook for Tabs
notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, sticky="nsew")

# Create frames for each tab
tables = {
    'tbl_user': ('pk_tbl_user', {
        'tbl_user_name': 'Name',
        'tbl_user_email': 'Email',
        'tbl_user_AccountNumber': 'Account Number',
        'tbl_user_IDNumber': 'ID Number'
    }),
    'tbl_Account': ('pk_tbl_account', {
        'tbl_account_name': 'Name',
        'tbl_account_id': 'Account ID',
        'tbl_account_password': 'Password',
        'tbl_account_server': 'Server',
        'tbl_account_active': 'Active',
        'tbl_account_mainaccount': 'Main Account'
    }),
    'tbl_ActiveTrade': ('tbl_ActiveTrade_TicketNr', {
        'tbl_ActiveTrade_TicketNr': 'Ticket Number'
    }),
    'tbl_trade': ('pk_tbl_trade', {
        'tbl_trade_account': 'Account',
        'tbl_trade_ticket': 'Ticket',
        'tbl_trade_magic': 'Magic',
        'tbl_trade_volume': 'Volume',
        'tbl_trade_profit': 'Profit',
        'tbl_trade_symbol': 'Symbol',
        'tbl_trade_billed': 'Billed'
    }),
    'tbl_Communication': ('pk_tbl_Communication', {
        'tbl_Communication_AccountNumber': 'Account Number',
        'tbl_Communication_Time': 'Time',
        'tbl_Communication_Message': 'Message'
    })
}

treeviews = {}
for table, (pk, columns) in tables.items():
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=table)

    # Labels and Entries
    entries = {}
    checkboxes = {}
    row_offset = 0
    for i, (col, text) in enumerate(columns.items()):
        ttk.Label(frame, text=text).grid(row=i + row_offset, column=0, padx=5, pady=5, sticky=tk.W)
        
        if col in ['tbl_account_active', 'tbl_account_mainaccount']:
            var = tk.IntVar()
            checkbox = ttk.Checkbutton(frame, variable=var)
            checkbox.grid(row=i + row_offset, column=1, padx=5, pady=5)
            checkboxes[col] = var
        else:
            entry = ttk.Entry(frame)
            entry.grid(row=i + row_offset, column=1, padx=5, pady=5)
            entries[col] = entry

    if table == 'tbl_trade':
        # Search functionality for tbl_trade
        ttk.Button(frame, text="Search", command=lambda tbl=table, ent=entries: search_records(tbl, ent)).grid(row=len(columns) + row_offset, column=0, padx=5, pady=5)
    elif table == 'tbl_Communication':
        # Search and Delete functionality for tbl_Communication
        ttk.Button(frame, text="Search", command=lambda tbl=table, ent=entries: search_records(tbl, ent)).grid(row=len(columns) + row_offset, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Delete", command=lambda tbl=table, pk=pk: delete_record(tbl, pk)).grid(row=len(columns) + row_offset, column=1, padx=5, pady=5)
    else:
        # Insert, Update, Delete, and Clear buttons for other tables
        ttk.Button(frame, text="Insert", command=lambda tbl=table, ent=entries, cb=checkboxes: insert_record(tbl, ent, cb)).grid(row=len(columns) + row_offset, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Update", command=lambda tbl=table, ent=entries, pk=pk, cb=checkboxes: update_record(tbl, ent, pk, cb)).grid(row=len(columns) + row_offset, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Delete", command=lambda tbl=table, pk=pk: delete_record(tbl, pk)).grid(row=len(columns) + row_offset, column=2, padx=5, pady=5)
        ttk.Button(frame, text="Clear", command=lambda ent=entries, cb=checkboxes: clear_entries(ent, cb)).grid(row=len(columns) + row_offset, column=3, padx=5, pady=5)

    # Treeview
    cols = [pk] + list(columns.keys())
    tree = ttk.Treeview(frame, columns=cols, show='headings')
    for col in cols:
        tree.heading(col, text=col)
    tree.grid(row=len(columns) + 1 + row_offset, column=0, columnspan=4, padx=5, pady=5)
    tree.bind("<ButtonRelease-1>", lambda event, tbl=table, ent=entries, cb=checkboxes: on_tree_select(event, tbl, ent, cb))

    treeviews[table] = tree
    display_records(table, tree)

def search_records(table, entries):
    search_criteria = {col: entry.get() for col, entry in entries.items() if entry.get()}
    if not search_criteria:
        messagebox.showwarning("Search Warning", "No search criteria provided.")
        return

    query = f"SELECT * FROM {table} WHERE "
    conditions = []
    params = []

    for col, value in search_criteria.items():
        conditions.append(f"{col} LIKE ?")
        params.append(f"%{value}%")

    query += " AND ".join(conditions)
    display_records(table, treeviews[table], query, params)

root.mainloop()
