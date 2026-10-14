SELECT category, SUM(revenue) * 1.0 / SUM(units) FROM sales
GROUP BY category
ORDER BY MIN(rowid);
