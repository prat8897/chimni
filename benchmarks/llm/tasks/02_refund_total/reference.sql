SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'refund';
