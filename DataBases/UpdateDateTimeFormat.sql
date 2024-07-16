-- Update the date format in the table tbl_trade
UPDATE tbl_trade
SET tbl_trade_time = 
    SUBSTR(tbl_trade_time, 1, 4) || '-' ||    -- Extract and reformat the year
    SUBSTR(tbl_trade_time, 6, 2) || '-' ||    -- Extract and reformat the month
    SUBSTR(tbl_trade_time, 9, 2) || ' ' ||    -- Extract and reformat the day
    SUBSTR(tbl_trade_time, 12, 5) || ':16'    -- Extract and reformat the time, adding ':16' for seconds
WHERE tbl_trade_time LIKE '____.__.__ __:__'; -- Match the original format pattern
