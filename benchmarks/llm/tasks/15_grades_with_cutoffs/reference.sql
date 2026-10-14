SELECT CASE WHEN value >= :a_cut THEN 'A' WHEN value >= :b_cut THEN 'B' ELSE 'F' END
FROM scores ORDER BY rowid;
