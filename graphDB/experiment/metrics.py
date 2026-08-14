"""가중(Horvitz-Thompson) P/R/F1 스윕, PR-AUC, 최적 임계값.

각 표본 쌍에 weight=N_k/n_k 를 부여해, t가 구간 경계일 때 설계서의
bin 단위 추정식 `Σ_{구간≥t} N_k·p_k` 와 정확히 일치하는 일반화 형태다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def weighted_confusion(sample, labels, t):
    tp = fp = fn = 0.0
    for sp in sample:
        y = labels[sp.pair_id]
        pred = sp.sim >= t
        if pred and y == 1:
            tp += sp.weight
        elif pred and y == 0:
            fp += sp.weight
        elif (not pred) and y == 1:
            fn += sp.weight
    return tp, fp, fn


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f


def sweep(sample, labels, thresholds):
    rows = []
    for t in thresholds:
        p, r, f = prf(*weighted_confusion(sample, labels, float(t)))
        rows.append({"threshold": round(float(t), 2), "precision": p, "recall": r, "f1": f})
    return pd.DataFrame(rows)


def best_threshold(df) -> float:
    m = df["f1"].max()
    return float(df.loc[df["f1"] >= m - 1e-12, "threshold"].min())


def pr_auc(df) -> float:
    d = df.sort_values("recall")
    # numpy 2.0 에서 trapz → trapezoid 로 개명. 양쪽 호환.
    trap = getattr(np, "trapezoid", None) or np.trapz
    return float(trap(d["precision"].values, d["recall"].values))
