SELECT SUM(tbl_trade_profit) + SUM(tbl_trade_swap) as total_profit
FROM Tbl_trade 
WHERE tbl_trade_account = 69885852 
  AND tbl_trade_time > '2024-07-21 00:00:00' 
  AND tbl_trade_type IN (0, 1);
