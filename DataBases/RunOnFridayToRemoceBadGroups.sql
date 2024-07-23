WITH magic_number_groups AS (
    SELECT 
        tbl_telegramGroup_MagicNumber AS magic_number, 
        tbl_telegramGroups_GroupName AS group_name
    FROM 
        tbl_telegramGroups
    WHERE 
        tbl_telegramGroup_ActiveIndicator = 1
),
daily_profits AS (
    SELECT 
        tbl_trade.tbl_trade_account,
        tbl_trade.tbl_trade_magic,
        DATE(tbl_trade.tbl_trade_time) AS trade_date,
        SUM(tbl_trade.tbl_trade_profit) AS daily_profit
    FROM 
        tbl_trade
    INNER JOIN 
        magic_number_groups ON tbl_trade.tbl_trade_magic = magic_number_groups.magic_number
    WHERE 
        tbl_trade.tbl_trade_account = 97576996 AND
        tbl_trade.tbl_trade_time BETWEEN '2024-01-01' AND '2024-07-23'
    GROUP BY 
        tbl_trade.tbl_trade_account, tbl_trade.tbl_trade_magic, DATE(tbl_trade.tbl_trade_time)
),
profitability_counts AS (
    SELECT 
        daily_profits.tbl_trade_magic,
        SUM(CASE WHEN daily_profits.daily_profit > 0 THEN 1 ELSE 0 END) AS profitable_days,
        SUM(CASE WHEN daily_profits.daily_profit <= 0 THEN 1 ELSE 0 END) AS non_profitable_days
    FROM 
        daily_profits
    GROUP BY 
        daily_profits.tbl_trade_magic
),
largest_trades AS (
    SELECT 
        tbl_trade.tbl_trade_magic,
        MAX(tbl_trade.tbl_trade_profit) AS largest_winning_trade,
        MIN(tbl_trade.tbl_trade_profit) AS largest_losing_trade
    FROM 
        tbl_trade
    WHERE 
        tbl_trade.tbl_trade_account = 97576996 AND
        tbl_trade.tbl_trade_time BETWEEN '2024-01-01' AND '2024-07-23'
    GROUP BY 
        tbl_trade.tbl_trade_magic
),
detailed_profits AS (
    SELECT 
        tbl_trade.tbl_trade_account,
        tbl_trade.tbl_trade_magic,
        magic_number_groups.group_name,
        MIN(tbl_trade.tbl_trade_time) AS date_from,
        MAX(tbl_trade.tbl_trade_time) AS date_to,
        SUM(tbl_trade.tbl_trade_profit) AS total_profit,
        profitability_counts.profitable_days,
        profitability_counts.non_profitable_days,
        largest_trades.largest_winning_trade,
        largest_trades.largest_losing_trade,
        CASE 
            WHEN largest_trades.largest_losing_trade = 0 THEN 'Undefined'
            ELSE
                CASE 
                    WHEN ABS(largest_trades.largest_losing_trade) > largest_trades.largest_winning_trade THEN 
                        ROUND(largest_trades.largest_winning_trade / ABS(largest_trades.largest_losing_trade), 2) * -1
                    ELSE 
                        ROUND(largest_trades.largest_winning_trade / ABS(largest_trades.largest_losing_trade), 2)
                END
        END AS win_loss_ratio
    FROM 
        tbl_trade
    INNER JOIN 
        magic_number_groups ON tbl_trade.tbl_trade_magic = magic_number_groups.magic_number
    INNER JOIN 
        profitability_counts ON tbl_trade.tbl_trade_magic = profitability_counts.tbl_trade_magic
    INNER JOIN 
        largest_trades ON tbl_trade.tbl_trade_magic = largest_trades.tbl_trade_magic
    WHERE 
        tbl_trade.tbl_trade_account = 97576996 AND
        tbl_trade.tbl_trade_time BETWEEN '2024-01-01' AND '2024-07-23'
    GROUP BY 
        tbl_trade.tbl_trade_account, tbl_trade.tbl_trade_magic, magic_number_groups.group_name, profitability_counts.profitable_days, profitability_counts.non_profitable_days, largest_trades.largest_winning_trade, largest_trades.largest_losing_trade
)
SELECT 
    tbl_trade_account,
    tbl_trade_magic,
    group_name,
    date_from,
    date_to,
    total_profit,
    profitable_days,
    non_profitable_days,
    largest_winning_trade,
    largest_losing_trade,
    win_loss_ratio
FROM 
    detailed_profits
WHERE 
    win_loss_ratio BETWEEN -0.3 AND 0 AND total_profit < 0
ORDER BY 
    win_loss_ratio DESC;
