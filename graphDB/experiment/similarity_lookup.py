"""code→code 하이브리드 유사도 lookup (RQ2 오프라인 재계산용).

RQ2는 환경이 둘로 갈린다: 유사도 계산(sbert)은 graphDB 3.11 환경에서 수행해
디스크로 덤프하고, 평가(backend)는 루트 3.12 환경에서 덤프를 로드한다.
"""
from __future__ import annotations

import json

import numpy as np

_SEP = ""  # 학수번호에 나오지 않는 구분자


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


def save_lookup(lut, path: str) -> None:
    """튜플 키 → 'a\\x01b' 문자열 키 JSON 으로 저장(환경 간 이식)."""
    obj = {f"{a}{_SEP}{b}": v for (a, b), v in lut.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def load_lookup(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    return {tuple(k.split(_SEP)): float(v) for k, v in obj.items()}
