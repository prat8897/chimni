SELECT id FROM transactions WHERE type = 'refund' OR amount > :limit ORDER BY rowid;
