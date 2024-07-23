WITH weekly_profits AS (
    SELECT 
        tbl_trade.tbl_trade_account,
        tbl_trade.tbl_trade_magic,
        date(tbl_trade.tbl_trade_time, 'weekday 0', '-6 days') AS week_start, -- Adjust to make week start from Sunday
        tbl_telegramGroups.tbl_telegramGroups_GroupName AS group_name,
        SUM(tbl_trade.tbl_trade_profit) AS weekly_profit
    FROM 
        tbl_trade
    INNER JOIN 
        tbl_telegramGroups ON tbl_trade.tbl_trade_magic = tbl_telegramGroups.tbl_telegramGroup_MagicNumber
    WHERE 
        tbl_trade.tbl_trade_account = 97576996
    GROUP BY 
        tbl_trade.tbl_trade_account, tbl_trade.tbl_trade_magic, week_start, tbl_telegramGroups.tbl_telegramGroups_GroupName
),
profitability_counts AS (
    SELECT 
        weekly_profits.tbl_trade_magic,
        weekly_profits.group_name,
        SUM(CASE WHEN weekly_profits.weekly_profit > 0 THEN 1 ELSE 0 END) AS profitable_weeks,
        SUM(CASE WHEN weekly_profits.weekly_profit <= 0 THEN 1 ELSE 0 END) AS non_profitable_weeks,
        CASE 
            WHEN SUM(CASE WHEN weekly_profits.weekly_profit <= 0 THEN 1 ELSE 0 END) = 0 
            THEN 'Yes' 
            ELSE 'No' 
        END AS only_profitable_weeks
    FROM 
        weekly_profits
    GROUP BY 
        weekly_profits.tbl_trade_magic, weekly_profits.group_name
),
detailed_profits AS (
    SELECT 
        weekly_profits.tbl_trade_account,
        weekly_profits.tbl_trade_magic,
        weekly_profits.group_name,
        weekly_profits.week_start,
        SUM(weekly_profits.weekly_profit) AS total_profit,
        profitability_counts.profitable_weeks,
        profitability_counts.non_profitable_weeks,
        profitability_counts.only_profitable_weeks
    FROM 
        weekly_profits
    INNER JOIN 
        profitability_counts ON weekly_profits.tbl_trade_magic = profitability_counts.tbl_trade_magic
    WHERE 
        weekly_profits.tbl_trade_account = 97576996
    GROUP BY 
        weekly_profits.tbl_trade_account, weekly_profits.tbl_trade_magic, weekly_profits.group_name, weekly_profits.week_start, profitability_counts.profitable_weeks, profitability_counts.non_profitable_weeks, profitability_counts.only_profitable_weeks
)
SELECT 
    tbl_trade_account,
    tbl_trade_magic,
    group_name,
    week_start,
    total_profit
FROM 
    detailed_profits
ORDER BY 
    group_name,week_start, total_profit DESC;
