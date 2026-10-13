def summarize_orders(orders, min_total):
    totals = {}
    for order in orders:
        name = order["customer"]
        totals[name] = totals.get(name, 0) + order["amount"]

    big_spenders = [(name, total) for name, total in totals.items() if total > min_total]
    big_spenders.sort(key=lambda pair: pair[1], reverse=True)
    return big_spenders
