SELECT AVG(value) FROM (
  SELECT value FROM times ORDER BY value
  LIMIT 2 - (SELECT COUNT(*) FROM times) % 2
  OFFSET ((SELECT COUNT(*) FROM times) - 1) / 2
);
