"""층 내 재표집 부트스트랩으로 P/R/F1 곡선의 95% 신뢰구간과 t* 분포 산출."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from experiment.metrics import sweep, best_threshold


def bootstrap_curves(sample, labels, thresholds, n_boot: int = 1000, seed: int = 42):
    rng = np.random.default_rng(seed)
    by_bin = defaultdict(list)
    for sp in sample:
        by_bin[sp.bin_idx].append(sp)

    keys = ("precision", "recall", "f1")
    stacks = {k: [] for k in keys}
    tstars = []
    for _ in range(n_boot):
        resampled = []
        for members in by_bin.values():
            idx = rng.integers(0, len(members), size=len(members))
            resampled.extend(members[t] for t in idx)
        df = sweep(resampled, labels, thresholds)
        for k in keys:
            stacks[k].append(df[k].values)
        tstars.append(best_threshold(df))

    out = {}
    for k in keys:
        arr = np.vstack(stacks[k])
        out[f"{k}_lo"] = np.percentile(arr, 2.5, axis=0)
        out[f"{k}_hi"] = np.percentile(arr, 97.5, axis=0)
    out["tstar"] = np.array(tstars, dtype=float)
    return out
