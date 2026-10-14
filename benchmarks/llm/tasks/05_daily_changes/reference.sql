SELECT d FROM (
  SELECT value - LAG(value) OVER (ORDER BY rowid) AS d, rowid AS r FROM prices
) WHERE d IS NOT NULL ORDER BY r;
