WITH magic_number_groups AS (
    SELECT 2784583072 AS magic_number, 'Gold Scalper Ninja' AS group_name UNION ALL
    SELECT 2784583073, 'FABIO VIP SQUAD' UNION ALL
    SELECT 2784583074, 'THE FOREX BOAR 🚀' UNION ALL
    SELECT 2784583075, 'JDB Copy Signals' UNION ALL
    SELECT 2784583076, '‎سيد تجارة الفوركس' UNION ALL
    SELECT 2784583077, 'GOLD FATHER CHRIS' UNION ALL
    SELECT 2784583078, '𝘍𝘰𝘳𝘦𝘹 𝘎𝘰𝘭𝘥 𝘔𝘢𝘴𝘵𝘦𝘳' UNION ALL
    SELECT 2784583079, '𝗚𝗢𝗟𝗗 𝗣𝗥𝗢 𝗧𝗥𝗔𝗗𝗘𝗥' UNION ALL
    SELECT 2784583080, '𝘼𝙇𝙀𝙓 𝙓𝘼𝙐𝙐𝙎𝘿 𝘾𝙃𝘼𝙎𝙀𝙍 ➤' UNION ALL
    SELECT 2784583081, 'FOREX EMPIRE' UNION ALL
    SELECT 2784583082, 'GBPUSD+USDJPY(GOLD) SIGNALS' UNION ALL
    SELECT 2784583083, 'Loi''s Gold TradingRoom' UNION ALL
    SELECT 2784583084, 'DENMARKPFOREX' UNION ALL
    SELECT 2784583085, 'Gold Snipers Fx - Free Gold Signals' UNION ALL
    SELECT 2784583086, '𝐆𝐎𝐋𝐃 𝐓𝐑𝐀𝐃𝐈𝐍𝐆 𝐀𝐂𝐀𝐃𝐄𝐌𝐘' UNION ALL
    SELECT 2784583087, 'Forex Scalping Strategy 📈' UNION ALL
    SELECT 2784583088, 'Mr Beast Gold' UNION ALL
    SELECT 2784583089, 'Areval Forex™' UNION ALL
    SELECT 2784583090, 'FX UNIQUE TRADE 😍😍😍' UNION ALL
    SELECT 2784583091, '🍀KING GOLD FOREX🍀🍀' UNION ALL
    SELECT 2784583092, 'King Of Gold⚡️' UNION ALL
    SELECT 2784583093, 'GOLD MASTER' UNION ALL
    SELECT 2784583094, 'FOREX TRADING SIGNAL(free)' UNION ALL
    SELECT 2784583095, 'XAUUSD GBPUSD' UNION ALL
    SELECT 2784583096, 'Chef Hazzim Scalping Maut🏆' UNION ALL
    SELECT 2784583097, 'MorganAK1®' UNION ALL
    SELECT 2784583098, 'Exnees account manager' UNION ALL
    SELECT 2784583099, '𝙂𝙤𝙡𝙙 𝘽𝙡𝙪𝙚 𝙥𝙞𝙥𝙨 ®' UNION ALL
    SELECT 2784583100, 'MXGOLDTRADE' UNION ALL
    SELECT 2784583101, 'FOREX CHAMPION' UNION ALL
    SELECT 2784583102, 'Forex Signals🔥💰 XAUUSD' UNION ALL
    SELECT 2784583103, '🔰PREMIUM Fx Signals💯' UNION ALL
    SELECT 2784583104, '𝐅𝐎𝐑𝐄𝐗 𝐕𝐈𝐏 𝐓𝐑𝐀𝐃𝐈𝐍𝐆™ ⚡️' UNION ALL
    SELECT 2784583105, 'Daily Forex Signals' UNION ALL
    SELECT 2784583106, 'APEX BULL FO®EX SIGNALS (free)'
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
        tbl_trade.tbl_trade_time BETWEEN '2024-07-01' AND '2024-07-31'  -- Adjust date range as needed
    GROUP BY 
        tbl_trade.tbl_trade_account, tbl_trade.tbl_trade_magic, DATE(tbl_trade.tbl_trade_time)
),
profitability_counts AS (
    SELECT 
        daily_profits.tbl_trade_magic,
        SUM(CASE WHEN daily_profits.daily_profit > 0 THEN 1 ELSE 0 END) AS profitable_days,
        SUM(CASE WHEN daily_profits.daily_profit <= 0 THEN 1 ELSE 0 END) AS non_profitable_days,
        CASE 
            WHEN SUM(CASE WHEN daily_profits.daily_profit <= 0 THEN 1 ELSE 0 END) = 0 
            THEN 'Yes' 
            ELSE 'No' 
        END AS only_profitable_days
    FROM 
        daily_profits
    GROUP BY 
        daily_profits.tbl_trade_magic
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
        profitability_counts.only_profitable_days
    FROM 
        tbl_trade
    INNER JOIN 
        magic_number_groups ON tbl_trade.tbl_trade_magic = magic_number_groups.magic_number
    INNER JOIN 
        profitability_counts ON tbl_trade.tbl_trade_magic = profitability_counts.tbl_trade_magic
    WHERE 
        tbl_trade.tbl_trade_account = 97576996 AND
        tbl_trade.tbl_trade_time BETWEEN '2024-07-01' AND '2024-07-31'  -- Adjust date range as needed
    GROUP BY 
        tbl_trade.tbl_trade_account, tbl_trade.tbl_trade_magic, magic_number_groups.group_name, profitability_counts.profitable_days, profitability_counts.non_profitable_days, profitability_counts.only_profitable_days
)
SELECT * FROM detailed_profits
UNION ALL
SELECT 
    NULL AS tbl_trade_account,
    NULL AS tbl_trade_magic,
    'Total' AS group_name,
    NULL AS date_from,
    NULL AS date_to,
    SUM(total_profit) AS total_profit,
    SUM(profitable_days) AS profitable_days,
    SUM(non_profitable_days) AS non_profitable_days,
    CASE 
        WHEN SUM(non_profitable_days) = 0 
        THEN 'Yes' 
        ELSE 'No' 
    END AS only_profitable_days
FROM 
    detailed_profits
ORDER BY 
    total_profit DESC;
