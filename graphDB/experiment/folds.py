"""층 내 교차검증 분할 — 보정·지도학습 평가가 함께 쓴다.

표본이 유사도 구간으로 층화돼 있고 층마다 크기와 양성률이 크게 다르므로
(0.0–0.5 는 100쌍·양성 0, 0.9–1.0 은 17쌍·양성 13), 단순 무작위 분할은
어떤 폴드에 고유사 구간이 몰리는 사고를 낸다. 층 안에서 잘라 각 폴드가
모든 구간을 고르게 갖게 한다.
"""
from __future__ import annotations

import numpy as np


def band_stratified_folds(sample, n_folds: int = 5, seed: int = 42) -> dict[int, int]:
    """pair_id -> 폴드 번호(0..n_folds-1). 층(bin_idx) 안에서 순환 배정."""
    if n_folds < 2:
        raise ValueError(f"폴드는 2 이상이어야 합니다: {n_folds}")
    rng = np.random.default_rng(seed)
    by_bin: dict[int, list] = {}
    for sp in sample:
        by_bin.setdefault(sp.bin_idx, []).append(sp)
    folds: dict[int, int] = {}
    for _, members in sorted(by_bin.items()):
        for rank, m in enumerate(rng.permutation(len(members))):
            folds[members[m].pair_id] = rank % n_folds
    return folds
