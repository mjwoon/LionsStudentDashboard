r"""비용 민감 임계값 선택과 t* 의 불안정성 정량화.

RQ1 의 t\* 는 가중 F1 을 최대화하는 지점이다. F1 은 오탐과 미탐을 같은 무게로
보지만 이 도메인의 비용은 비대칭이다 — 무관한 과목을 인정하면(FP) 적합도가
부풀려져 학사 판단을 오도하는 반면, 놓치면(FN) 과소 계상에 그친다.

여기서는 두 가지를 제공한다.

1. **비용 민감 임계값** — 비용비 lam = c_FP / c_FN 에 대해
   `cost(t) = lam · FP(t) + FN(t)` 를 최소화하는 t\*(lam).
   단일 점추정 대신 의사결정 프런티어로 임계값을 제시한다.
2. **t\* 분포 요약** — 부트스트랩 t\* 표본의 산포(sd·CV·IQR·최빈값).
   희소 양성에서 argmax 계열 임계값은 그 자체가 잡음이 큰 통계량이므로,
   한계를 서술로 인정하는 대신 측정치로 보고한다.

가중치는 metrics 모듈과 동일한 Horvitz–Thompson 역표집확률 가중을 쓴다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from experiment.metrics import weighted_confusion, prf


def weighted_cost(sample, labels, t: float, lam: float) -> float:
    """lam · FP(t) + FN(t) (모두 모집단 가중)."""
    _, fp, fn = weighted_confusion(sample, labels, float(t))
    return lam * fp + fn


def cost_optimal_threshold(sample, labels, thresholds, lam: float) -> float:
    """cost 를 최소화하는 임계값. 동률이면 가장 낮은 값(더 관대한 쪽)을 택한다."""
    costs = np.array([weighted_cost(sample, labels, float(t), lam) for t in thresholds])
    return float(np.asarray(thresholds)[int(np.argmin(costs))])


def cost_curve(sample, labels, thresholds, lams) -> pd.DataFrame:
    """비용비별 최적 임계값과 그 지점의 성능.

    lam < 1 : 미탐이 더 비싸다(재현율 우선) → 임계값이 낮아진다
    lam = 1 : 오탐·미탐 동일 비용
    lam > 1 : 오탐이 더 비싸다(정밀도 우선) → 임계값이 높아진다
    """
    rows = []
    for lam in lams:
        t = cost_optimal_threshold(sample, labels, thresholds, float(lam))
        tp, fp, fn = weighted_confusion(sample, labels, t)
        p, r, f = prf(tp, fp, fn)
        rows.append({
            "lam": float(lam), "tstar": t,
            "precision": p, "recall": r, "f1": f,
            "tp": tp, "fp": fp, "fn": fn,
            "cost": weighted_cost(sample, labels, t, float(lam)),
        })
    return pd.DataFrame(rows)


def tstar_distribution(tstars) -> dict:
    """부트스트랩 t* 표본의 산포 요약."""
    arr = np.asarray(tstars, dtype=float)
    if arr.size == 0:
        raise ValueError("t* 표본이 비어 있습니다.")
    vals, counts = np.unique(np.round(arr, 4), return_counts=True)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=0))
    q1, q3 = (float(x) for x in np.percentile(arr, [25, 75]))
    return {
        "n": int(arr.size),
        "mean": mean,
        "sd": sd,
        "cv": float(sd / mean) if mean else float("inf"),
        "median": float(np.median(arr)),
        "mode": float(vals[int(np.argmax(counts))]),
        "mode_share": float(counts.max() / arr.size),
        "iqr": q3 - q1,
        "q1": q1,
        "q3": q3,
        "min": float(arr.min()),
        "max": float(arr.max()),
        "ci95": [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))],
    }
