SELECT id FROM transactions t
WHERE rowid = (SELECT MIN(rowid) FROM transactions u WHERE u.id = t.id)
  AND amount > :limit
ORDER BY rowid
LIMIT 1;
