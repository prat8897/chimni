def spenders_and_revenue(orders, min_total):
    totals = {}
    for order in orders:
        name = order["customer"]
        totals[name] = totals.get(name, 0) + order["amount"]

    big_spenders = [(name, total) for name, total in totals.items() if total > min_total]
    big_spenders.sort(key=lambda pair: pair[1], reverse=True)

    revenue = sum(order["amount"] for order in orders)
    return big_spenders, revenue
