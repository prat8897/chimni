SELECT value * 1.0 / (SELECT MAX(value) FROM scores) FROM scores ORDER BY rowid;
