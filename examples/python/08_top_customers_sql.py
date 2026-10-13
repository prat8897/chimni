# SELECT c.name, SUM(o.amount)
# FROM customers c JOIN orders o ON o.cid = c.id
# GROUP BY c.name ORDER BY 2 DESC LIMIT 3;
def top_customers(customers, orders):
    by_cid = {}
    for o in orders:
        by_cid.setdefault(o["cid"], []).append(o)
    totals = {}
    for c in customers:
        for o in by_cid.get(c["id"], []):
            totals[c["name"]] = totals.get(c["name"], 0) + o["amount"]
    return sorted(totals.items(), key=lambda p: p[1], reverse=True)[:3]
