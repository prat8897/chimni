SELECT category, name FROM (
  SELECT category, name,
         ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC, rowid) AS rn,
         MIN(rowid) OVER (PARTITION BY category) AS first_seen
  FROM products
) WHERE rn = 1 ORDER BY first_seen;
