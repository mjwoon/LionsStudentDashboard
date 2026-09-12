"""Cohen's κ (레이블러 간 신뢰도, 골드↔silver 일치도)."""
from __future__ import annotations


def confusion_2x2(a, b):
    n11 = sum(1 for x, y in zip(a, b) if x == 1 and y == 1)
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n00 = sum(1 for x, y in zip(a, b) if x == 0 and y == 0)
    return {"n11": n11, "n10": n10, "n01": n01, "n00": n00}


def cohen_kappa(a, b) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)
