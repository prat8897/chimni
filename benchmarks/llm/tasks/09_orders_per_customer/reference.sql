SELECT customer, COUNT(*) AS n FROM orders
GROUP BY customer
ORDER BY n DESC, MIN(rowid);
