import sqlite3
import pandas as pd
import streamlit as st
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Connect to SQLite database using a context manager
PATH = os.path.abspath(__file__)
DIRECTORY = os.path.dirname(os.path.dirname(PATH))
DB_CONNECTION = os.path.join(DIRECTORY, "DataBases", "CopyTradingV2.db")

def get_data(query):
    try:
        with sqlite3.connect(DB_CONNECTION) as conn:
            return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"An error occurred while querying the database: {e}")
        return pd.DataFrame()

# Calculate default dates for Monday and Friday of the current week
today = datetime.today()
monday = today - timedelta(days=today.weekday())
friday = monday + timedelta(days=4)

# Date selectors
start_date = st.date_input("Start Date", monday)
end_date = st.date_input("End Date", friday)

# Max Trade Pips input box
max_trade_pips = st.number_input("Max Trade Pips", min_value=1, value=20)

# Convert dates to strings for the query
start_date_str = start_date.strftime('%Y-%m-%d 00:00:00')
end_date_str = end_date.strftime('%Y-%m-%d 23:59:59')

# Query to read data from tbl_trade and join with tbl_telegramGroups to get group names
query_all = f"""
SELECT t.*, g.tbl_telegramGroups_GroupName
FROM tbl_trade t
JOIN tbl_telegramGroups g ON t.tbl_trade_magic = g.tbl_telegramGroup_MagicNumber
WHERE t.tbl_trade_account = 97576996 
AND t.tbl_trade_timeOpen BETWEEN '{start_date_str}' AND '{end_date_str}'
AND t.tbl_trade_profit != 0
AND (
    SELECT COUNT(*) 
    FROM tbl_trade t2
    WHERE 
    t.tbl_trade_account = 97576996 AND 
    t2.tbl_trade_magic = t.tbl_trade_magic AND 
    t2.tbl_trade_profit != 0
) > 1
AND tbl_telegramGroup_ActiveIndicator = 1


"""
# AND (
#     (t.tbl_trade_type = 0 AND ABS(t.tbl_trade_Price - t.tbl_trade_tp) < {max_trade_pips} AND ABS(t.tbl_trade_Price - t.tbl_trade_sl) < {max_trade_pips}) OR
#     (t.tbl_trade_type = 1 AND ABS(t.tbl_trade_tp - t.tbl_trade_Price) < {max_trade_pips} AND ABS(t.tbl_trade_sl - t.tbl_trade_Price) < {max_trade_pips})
# )
def analyze_data(df):
    # Calculate the trade duration
    df['tbl_trade_timeOpen'] = pd.to_datetime(df['tbl_trade_timeOpen'])
    df['tbl_trade_timeClose'] = pd.to_datetime(df['tbl_trade_timeClose'], errors='coerce')
    df['trade_duration'] = (df['tbl_trade_timeClose'] - df['tbl_trade_timeOpen']).dt.total_seconds() / 60  # Duration in minutes

    # Group by tbl_trade_magic and calculate the total profit, number of profitable trades, and number of losing trades for each group
    analysis = df.groupby(['tbl_trade_magic', 'tbl_telegramGroups_GroupName']).agg(
        total_profit=pd.NamedAgg(column='tbl_trade_profit', aggfunc='sum'),
        total_trades=pd.NamedAgg(column='pk_tbl_trade', aggfunc='count'),
        profitable_trades=pd.NamedAgg(column='tbl_trade_profit', aggfunc=lambda x: (x > 0).sum()),
        losing_trades=pd.NamedAgg(column='tbl_trade_profit', aggfunc=lambda x: (x <= 0).sum()),
        max_drawdown=pd.NamedAgg(column='tbl_trade_drawdown', aggfunc='min'),
        average_trade_duration=pd.NamedAgg(column='trade_duration', aggfunc='mean'),
        open_trades=pd.NamedAgg(column='tbl_trade_timeClose', aggfunc=lambda x: x.isna().sum())  # Count open trades
    ).reset_index()

    # Calculate profitable and losing days
    df['trade_date'] = pd.to_datetime(df['tbl_trade_timeOpen']).dt.date
    daily_profit = df.groupby(['tbl_trade_magic', 'tbl_telegramGroups_GroupName', 'trade_date']).agg(
        daily_profit=pd.NamedAgg(column='tbl_trade_profit', aggfunc='sum')
    ).reset_index()
    daily_analysis = daily_profit.groupby(['tbl_trade_magic', 'tbl_telegramGroups_GroupName']).agg(
        profitable_days=pd.NamedAgg(column='daily_profit', aggfunc=lambda x: (x > 0).sum()),
        losing_days=pd.NamedAgg(column='daily_profit', aggfunc=lambda x: (x <= 0).sum())
    ).reset_index()

    # Merge daily analysis with the main analysis
    analysis = analysis.merge(daily_analysis, on=['tbl_trade_magic', 'tbl_telegramGroups_GroupName'])

    # Additional metrics
    analysis['win_rate'] = (analysis['profitable_trades'] / analysis['total_trades']) * 100
    analysis['average_profit'] = analysis['total_profit'] / analysis['total_trades']
    analysis['profit_factor'] = analysis.apply(lambda row: row['total_profit'] / abs(row['losing_trades'] if row['losing_trades'] != 0 else 1), axis=1)

    return analysis


# Load data into a DataFrame for overall analysis
df_all = get_data(query_all)

# Analyze the data
if not df_all.empty:
    analysis = analyze_data(df_all)

    # Separate good and bad groups for other tabs
    good_groups = analysis[analysis['total_profit'] > 0].sort_values(by='total_profit', ascending=False)
    bad_groups = analysis[analysis['total_profit'] <= 0].sort_values(by='total_profit', ascending=True)

    # Calculate the number of signal groups
    total_groups = df_all['tbl_trade_magic'].nunique()

    # Streamlit app to display the analysis results
    st.title('Telegram Signal Group Analysis')

    # Display data in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["All Signal Groups", "Good Signal Groups", "Bad Signal Groups", "Summary"])

    with tab1:
        st.header('All Signal Groups')
        
        # Sort and display the dataframe grouped by signal group
        analysis_sorted = analysis.sort_values(by='total_profit', ascending=False)
        st.dataframe(analysis_sorted)
        
        # Searchable dropdown with a text input box
        search_query = st.text_input("Search for a Signal Group")
        filtered_groups = analysis_sorted['tbl_telegramGroups_GroupName'].unique()

        if search_query:
            filtered_groups = [group for group in filtered_groups if search_query.lower() in group.lower()]

        selected_group_name = st.selectbox("Select Signal Group", filtered_groups)

        if selected_group_name:
            df_filtered = df_all[df_all['tbl_telegramGroups_GroupName'] == selected_group_name]
            st.dataframe(df_filtered)
            
            # Continue with the rest of the code for plotting and analysis...

    with tab2:
        st.header('Good Signal Groups')
        st.dataframe(good_groups)

    with tab3:
        st.header('Bad Signal Groups')
        st.dataframe(bad_groups)

    with tab4:
        st.header('Summary')
        st.write(f'Total Signal Groups: {total_groups}')
        st.write(f'Good Signal Groups: {good_groups.shape[0]}')
        st.write(f'Bad Signal Groups: {bad_groups.shape[0]}')
else:
    st.warning("No data available for the selected date range.")
