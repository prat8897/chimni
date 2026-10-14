"""Trusted reference for 23_deviation_from_mean."""
def solve(measurements):
    if not measurements:
        return []
    mean = sum(measurements) / len(measurements)
    return [m - mean for m in measurements]
