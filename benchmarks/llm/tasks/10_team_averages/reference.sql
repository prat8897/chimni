SELECT team, AVG(score) FROM players
GROUP BY team
ORDER BY MIN(rowid);
