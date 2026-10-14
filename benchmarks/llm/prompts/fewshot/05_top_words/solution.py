def solve(text, n):
    counts = {}
    for w in text.lower().split():
        counts[w] = counts.get(w, 0) + 1
    return sorted(counts.items(), key=lambda p: p[1], reverse=True)[:n]
