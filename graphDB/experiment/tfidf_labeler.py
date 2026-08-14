"""TF-IDF silver 레이블: 교과목 이름 char n-gram TF-IDF cosine ≥ threshold → 1."""
from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from text_features import build_name_char_tfidf


def tfidf_labels(df, sample, threshold: float = 0.30):
    names = df["교과목 이름"].fillna("").tolist()
    vec = build_name_char_tfidf()
    mat = vec.fit_transform(names).toarray()
    mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)
    sim = cosine_similarity(mat)
    return {sp.pair_id: int(sim[sp.i][sp.j] >= threshold) for sp in sample}
