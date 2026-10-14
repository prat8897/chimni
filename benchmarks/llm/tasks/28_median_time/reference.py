"""Trusted reference for 28_median_time."""
import statistics


def solve(times):
    return statistics.median(times) if times else None
