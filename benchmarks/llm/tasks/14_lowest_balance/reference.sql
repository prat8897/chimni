SELECT MIN(b) FROM (SELECT SUM(amount) OVER (ORDER BY rowid) AS b FROM transactions);
