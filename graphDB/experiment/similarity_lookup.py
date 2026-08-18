"""code→code 하이브리드 유사도 lookup (RQ2 오프라인 재계산용)."""
from __future__ import annotations

import numpy as np


def build_lookup(df, sim, min_keep: float = 0.6):
    """학수번호 있는 쌍 중 sim ≥ min_keep 만 보관. 키는 정렬된 (code_a, code_b)."""
    codes = df["학수번호"].fillna("").astype(str).tolist()
    n = len(codes)
    lut = {}
    iu, ju = np.triu_indices(n, k=1)
    for i, j in zip(iu.tolist(), ju.tolist()):
        ci, cj = codes[i], codes[j]
        if not ci or not cj or ci == cj:
            continue
        s = float(sim[i][j])
        if s >= min_keep:
            key = (min(ci, cj), max(ci, cj))
            # 같은 코드쌍이 여러 행에 나오면 최대 유사도 유지
            if s > lut.get(key, 0.0):
                lut[key] = s
    return lut


def make_similarity_fn(lut):
    """대칭 조회 함수. 같은 코드면 1.0, 없으면 0.0."""
    def fn(a: str, b: str) -> float:
        if a == b:
            return 1.0
        return lut.get((min(a, b), max(a, b)), 0.0)
    return fn
