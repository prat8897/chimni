SELECT g, COUNT(*) FROM (
  SELECT rowid AS r, CASE WHEN value >= 90 THEN 'A' WHEN value >= 75 THEN 'B' ELSE 'C' END AS g FROM scores
)
GROUP BY g
ORDER BY MIN(r);
