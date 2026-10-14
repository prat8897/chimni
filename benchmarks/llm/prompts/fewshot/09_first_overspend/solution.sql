SELECT i FROM (
  SELECT rowid - 1 AS i, SUM(value) OVER (ORDER BY rowid) AS running FROM expenses
) WHERE running > :budget
ORDER BY i
LIMIT 1;
