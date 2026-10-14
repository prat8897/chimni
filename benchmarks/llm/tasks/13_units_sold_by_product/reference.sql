SELECT p.name, SUM(s.units) AS total
FROM products p JOIN sales s ON s.product_id = p.id
GROUP BY p.name
ORDER BY total DESC, MIN(p.rowid);
