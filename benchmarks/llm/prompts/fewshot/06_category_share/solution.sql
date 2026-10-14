SELECT cat, SUM(amount) * 1.0 / (SELECT SUM(amount) FROM sales) AS share
FROM sales
GROUP BY cat
ORDER BY MIN(rowid);
