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

# Convert dates to strings for the query
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

# Query to read data from tbl_trade and join with tbl_telegramGroups to get group names
query_all = f"""
SELECT t.*, g.tbl_telegramGroups_GroupName
FROM tbl_trade t
JOIN tbl_telegramGroups g ON t.tbl_trade_magic = g.tbl_telegramGroup_MagicNumber
WHERE t.tbl_trade_account = 97576996 
AND t.tbl_trade_time BETWEEN '{start_date_str}' AND '{end_date_str}'
AND t.tbl_trade_profit != 0
"""

# Load data into a DataFrame for overall analysis
df_all = get_data(query_all)

# Function to analyze the data and determine the best and worst signal groups
def analyze_data(df):
    # Group by tbl_trade_magic and calculate the total profit, number of profitable trades, and number of losing trades for each group
    analysis = df.groupby(['tbl_trade_magic', 'tbl_telegramGroups_GroupName']).agg(
        total_profit=pd.NamedAgg(column='tbl_trade_profit', aggfunc='sum'),
        total_trades=pd.NamedAgg(column='pk_tbl_trade', aggfunc='count'),
        profitable_trades=pd.NamedAgg(column='tbl_trade_profit', aggfunc=lambda x: (x > 0).sum()),
        losing_trades=pd.NamedAgg(column='tbl_trade_profit', aggfunc=lambda x: (x <= 0).sum()),
        max_drawdown=pd.NamedAgg(column='tbl_trade_drawdown', aggfunc='min')
    ).reset_index()

    # Calculate profitable and losing days
    df['trade_date'] = pd.to_datetime(df['tbl_trade_time']).dt.date
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

# Function to calculate the drawdown series
def calculate_drawdown(cumulative_profit):
    running_max = cumulative_profit.cummax()
    drawdown = cumulative_profit - running_max
    return drawdown

# Analyze the data
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
    
    # Display the dataframe grouped by signal group
    st.dataframe(analysis)
    
    selected_group_name = st.selectbox("Select Signal Group", analysis['tbl_telegramGroups_GroupName'].unique())
    
    if selected_group_name:
        df_filtered = df_all[df_all['tbl_telegramGroups_GroupName'] == selected_group_name]
        st.dataframe(df_filtered)
        
        # Calculate metrics for the selected signal group
        profitable_trades = df_filtered[df_filtered['tbl_trade_profit'] > 0].shape[0]
        losing_trades = df_filtered[df_filtered['tbl_trade_profit'] <= 0].shape[0]
        total_trades = df_filtered.shape[0]
        cumulative_profit = df_filtered['tbl_trade_profit'].cumsum()
        
        # Calculate drawdown
        drawdown = calculate_drawdown(cumulative_profit)

        # Plotting
        fig1, ax1 = plt.subplots()
        pd.Series([profitable_trades, losing_trades], index=['Profitable Trades', 'Losing Trades']).plot.pie(
            autopct='%1.1f%%', startangle=90, ax=ax1, legend=False)
        ax1.set_title('Profitable vs Losing Trades')
        st.pyplot(fig1)

        # Group trades by date
        trades_per_day = df_filtered.groupby('trade_date').size()

        fig2, ax2 = plt.subplots()
        trades_per_day.plot.bar(ax=ax2)
        ax2.set_title('Number of Trades per Day')
        ax2.set_ylabel('Number of Trades')
        ax2.set_xlabel('Date')
        st.pyplot(fig2)

        fig3, ax3 = plt.subplots()
        ax3.plot(df_filtered.index, cumulative_profit, label='Cumulative Profit')
        ax3.plot(df_filtered.index, drawdown, label='Drawdown', color='red')
        ax3.set_title(f'Cumulative Profit and Drawdown Over Time for {selected_group_name}')
        ax3.set_ylabel('Value')
        ax3.set_xlabel('Trade Index')
        ax3.legend()
        st.pyplot(fig3)

        fig4, ax4 = plt.subplots()
        df_filtered['tbl_trade_profit'].hist(bins=20, ax=ax4)
        ax4.set_title('Distribution of Profit/Loss per Trade')
        ax4.set_xlabel('Profit/Loss')
        ax4.set_ylabel('Frequency')
        st.pyplot(fig4)
        
        # Plotting daily profit and loss
        fig5, ax5 = plt.subplots()
        daily_profit_loss = df_filtered.groupby('trade_date')['tbl_trade_profit'].sum()
        daily_profit_loss.plot(kind='bar', ax=ax5)
        ax5.set_title('Daily Profit and Loss')
        ax5.set_ylabel('Profit/Loss')
        ax5.set_xlabel('Date')
        st.pyplot(fig5)

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
