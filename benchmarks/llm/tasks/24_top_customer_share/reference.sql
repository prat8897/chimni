SELECT MAX(t) * 1.0 / (SELECT SUM(amount) FROM orders)
FROM (SELECT SUM(amount) AS t FROM orders GROUP BY customer);
