def first_overspend(expenses, budget):
    running = 0
    for i, e in enumerate(expenses):
        running += e
        if running > budget:
            return i
    return None
