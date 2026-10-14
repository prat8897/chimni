SELECT day FROM events
GROUP BY day
HAVING COUNT(*) > :k
ORDER BY MIN(rowid);
