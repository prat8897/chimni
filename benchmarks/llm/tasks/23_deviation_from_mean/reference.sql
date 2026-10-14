SELECT value - (SELECT AVG(value) FROM measurements) FROM measurements ORDER BY rowid;
