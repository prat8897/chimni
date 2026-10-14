SELECT category, COUNT(*) AS c FROM items
GROUP BY category
ORDER BY c DESC, MIN(rowid)
LIMIT :n;
