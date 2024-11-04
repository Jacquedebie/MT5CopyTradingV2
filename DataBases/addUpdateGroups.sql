select * from tbl_telegramGroups
where tbl_telegramGroups_GroupName like '%FOREX ROYALTY%'


update tbl_telegramGroups
set tbl_telegramGroups_GroupName = '☘️Lemons Forex☘️'
where tbl_telegramGroup_MagicNumber = 2784583119

INSERT INTO tbl_telegramGroups 
(tbl_telegramGroups_GroupName, tbl_telegramGroup_MagicNumber, tbl_telegramGroup_ActiveIndicator, tbl_telegramGroup_DeactiveReason)
VALUES 
('FOREX ROYALTY™', 
(SELECT IFNULL(MAX(tbl_telegramGroup_MagicNumber), 0) + 1 FROM tbl_telegramGroups), 
1, -- or the appropriate value for ActiveIndicator
'');