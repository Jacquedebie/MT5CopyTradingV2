SELECT 
    t.tbl_trade_magic,
    g.tbl_telegramGroups_GroupName,
    COUNT(*) AS trade_count,
    SUM(t.tbl_trade_volume) AS total_volume,
    SUM(t.tbl_trade_profit) AS total_profit,
    SUM(t.tbl_trade_swap) AS total_swap,
    SUM(t.tbl_trade_drawdown) AS total_drawdown,
    SUM(t.tbl_trade_maxProfit) AS total_maxProfit,
    SUM(SUM(t.tbl_trade_profit)) OVER () AS total_profit_overall,
    AVG(
        CASE 
            WHEN t.tbl_trade_type = 2 THEN (t.tbl_trade_tp - t.tbl_trade_price)
            WHEN t.tbl_trade_type = 1 THEN (t.tbl_trade_price - t.tbl_trade_tp)
            ELSE 0
        END
    ) AS avg_tp_price_diff,
    AVG(
        CASE 
            WHEN t.tbl_trade_type = 1 THEN (t.tbl_trade_sl - t.tbl_trade_price)
            WHEN t.tbl_trade_type = 2 THEN (t.tbl_trade_price - t.tbl_trade_sl)
            ELSE 0
        END
    ) AS avg_sl_price_diff,
    CASE 
        WHEN AVG(
                CASE 
                    WHEN t.tbl_trade_type = 1 THEN (t.tbl_trade_sl - t.tbl_trade_price)
                    WHEN t.tbl_trade_type = 2 THEN (t.tbl_trade_price - t.tbl_trade_sl)
                    ELSE 0
                END
            ) = 0 THEN NULL
        ELSE AVG(
                CASE 
                    WHEN t.tbl_trade_type = 2 THEN (t.tbl_trade_tp - t.tbl_trade_price)
                    WHEN t.tbl_trade_type = 1 THEN (t.tbl_trade_price - t.tbl_trade_tp)
                    ELSE 0
                END
            ) / AVG(
                CASE 
                    WHEN t.tbl_trade_type = 1 THEN (t.tbl_trade_sl - t.tbl_trade_price)
                    WHEN t.tbl_trade_type = 2 THEN (t.tbl_trade_price - t.tbl_trade_sl)
                    ELSE 0
                END
            )
    END AS ratio
FROM tbl_trade t
INNER JOIN tbl_telegramGroups g
    ON t.tbl_trade_magic = g.tbl_telegramGroup_MagicNumber
WHERE t.tbl_trade_timeOpen >= '2024-09-03 00:00:00'
  AND t.tbl_trade_timeOpen < '2024-09-04 00:00:00'
  AND t.tbl_trade_account = '97576996'
GROUP BY t.tbl_trade_magic, g.tbl_telegramGroups_GroupName
order by ratio desc
