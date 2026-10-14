SELECT customer, SUM(amount) AS total
FROM orders
GROUP BY customer
HAVING total > :min_total
ORDER BY total DESC, MIN(rowid);
