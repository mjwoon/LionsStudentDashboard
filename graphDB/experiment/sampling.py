"""유사도 구간별 층화 표본 추출 + 층별 모집단 크기(N_k)·역표집확률 가중치."""
from __future__ import annotations

import numpy as np

from experiment.pairs import SampledPair

BINS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]


def bin_index(sim: float) -> int:
    """유사도 → 구간 인덱스(0..5). 범위 밖이면 -1."""
    for k, (lo, hi) in enumerate(BINS):
        if lo <= sim < hi:
            return k
    return -1


def stratified_sample(pairs, sims, per_bin, seed: int = 42):
    """구간별로 per_bin[k]개 추출. 반환: (SampledPair 리스트, N_k 리스트).

    각 표본에 weight = N_k / n_k (역표집확률) 부여.
    """
    rng = np.random.default_rng(seed)
    bins = np.array([bin_index(float(s)) for s in sims])
    sample: list[SampledPair] = []
    N_k: list[int] = []
    pid = 0
    for k in range(len(BINS)):
        idx = np.nonzero(bins == k)[0]
        N = len(idx)
        N_k.append(N)
        take = min(per_bin[k], N)
        chosen = rng.choice(idx, size=take, replace=False) if take else np.array([], dtype=int)
        weight = (N / take) if take else 0.0
        for c in sorted(int(x) for x in chosen):
            i, j = int(pairs[c][0]), int(pairs[c][1])
            sample.append(SampledPair(pid, i, j, float(sims[c]), k, weight))
            pid += 1
    return sample, N_k
