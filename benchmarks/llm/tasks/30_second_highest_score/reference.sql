SELECT MAX(value) FROM scores WHERE value < (SELECT MAX(value) FROM scores);
