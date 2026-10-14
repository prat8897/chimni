-- tables: customers(id, name), orders(id, cid, amount)
SELECT c.name, SUM(o.amount) AS total
FROM customers c JOIN orders o ON o.cid = c.id
GROUP BY c.name
ORDER BY total DESC, MIN(c.rowid)
LIMIT 3;
