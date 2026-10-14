SELECT c.name
FROM customers c JOIN orders o ON o.customer_id = c.id
GROUP BY c.name
HAVING SUM(o.amount) >= :min_total
ORDER BY c.name;
