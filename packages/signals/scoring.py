import math


def bounded_score(raw: float, scale: float) -> float:
    """Map an unbounded raw signal to a 0-100 score, 50 = neutral, via tanh.

    ``scale`` is the raw magnitude that saturates the score near 0/100.
    """
    return 50.0 + 50.0 * math.tanh(raw / scale)


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
