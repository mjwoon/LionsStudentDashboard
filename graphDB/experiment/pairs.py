"""유효 쌍 추출 + 프로덕션 하이브리드 유사도 계산 (실험 공통 데이터 원천)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from text_features import is_sequential_course


@dataclass
class SampledPair:
    pair_id: int
    i: int
    j: int
    sim: float
    bin_idx: int
    weight: float


def valid_pair_indices(df: pd.DataFrame) -> np.ndarray:
    """같은 학수번호 쌍·연계과목(1,2 시리즈) 쌍을 제외한 상삼각 (i,j) 인덱스."""
    codes = (
        df["학수번호"].fillna("").astype(str).tolist()
        if "학수번호" in df.columns
        else [""] * len(df)
    )
    names = df["교과목 이름"].tolist()
    n = len(df)
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            if codes[i] and codes[i] == codes[j]:
                continue
            if is_sequential_course(names[i], names[j]):
                continue
            out.append((i, j))
    return np.array(out, dtype=int) if out else np.empty((0, 2), dtype=int)


def compute_hybrid_similarity(df: pd.DataFrame, engine=None) -> np.ndarray:
    """프로덕션 하이브리드(0.7·SBERT + 0.3·TF-IDF) n×n 유사도 행렬.

    engine=None 이면 실제 SBERT 모델을 로드한다.
    """
    from similarity_engine import SimilarityEngine

    if engine is None:
        engine = SimilarityEngine()
    if "feature_text" not in df.columns:
        df = df.copy()
        df["feature_text"] = df["교과목 이름"] + " " + df["교과목개요"].fillna("")
    emb = engine.create_embeddings(df, use_tfidf_weighting=True)
    return engine._similarity_matrix(emb)
