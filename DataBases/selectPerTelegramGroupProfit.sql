WITH magic_number_groups AS (
    SELECT 2784583072 AS magic_number, 'Gold Scalper Ninja' AS group_name UNION ALL
    SELECT 2784583073, 'FABIO VIP SQUAD' UNION ALL
    SELECT 2784583074, 'THE FOREX BOAR 🚀' UNION ALL
    SELECT 2784583075, 'JDB Copy Signals' UNION ALL
    SELECT 2784583076, '‎سيد تجارة الفوركس' UNION ALL
    SELECT 2784583077, 'GOLD FATHER CHRIS' UNION ALL
    SELECT 2784583078, '𝘍𝘰𝘳𝘦𝘹 𝘎𝘰𝘭𝘥 𝘔𝘢𝘴𝘵𝘦𝘳' UNION ALL
    SELECT 2784583079, '𝗚𝗢𝗟𝗗 𝗣𝗥𝗢 𝗧𝗥𝗔𝗗𝗘𝗥'
)
SELECT 
    tbl_trade_account,
    tbl_trade_magic,
    group_name,
    SUM(tbl_trade_profit) AS total_profit
FROM 
    tbl_trade
LEFT JOIN 
    magic_number_groups ON tbl_trade_magic = magic_number_groups.magic_number
WHERE 
    tbl_trade_time BETWEEN '2024-07-07' AND '2024-07-14'  -- Adjust date range as needed
GROUP BY 
    tbl_trade_account, tbl_trade_magic, group_name
order by group_name	DESC;
