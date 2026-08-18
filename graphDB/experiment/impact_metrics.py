"""RQ2 하위 영향 지표: 학과 순위(Spearman ρ), Top-1 변경률, 등급 이동.

scipy 의존 없이 Spearman ρ를 numpy(평균 순위 + Pearson)로 직접 구현한다
→ RQ2 실행 환경(루트 3.12)에 scipy 미설치여도 동작.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ranked(df):
    out = {}
    for sid, g in df.groupby("student_id"):
        s = g.sort_values("department_id")
        out[sid] = dict(zip(s["department_id"], s["overall_score"]))
    return out


def _rankdata(values) -> np.ndarray:
    """오름차순 평균 순위(동점은 평균). scipy.stats.rankdata('average')와 동일."""
    a = np.asarray(values, dtype=float)
    order = a.argsort()
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)
    # 동점 처리: 같은 값끼리 평균 순위로 치환
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def _spearman(x, y) -> float:
    rx, ry = _rankdata(x), _rankdata(y)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return 1.0
    return float(np.corrcoef(rx, ry)[0, 1])


def top1_change_rate(df, base_df) -> float:
    a, b = _ranked(df), _ranked(base_df)
    changed = total = 0
    for sid in b:
        if sid not in a:
            continue
        total += 1
        top_b = max(b[sid], key=b[sid].get)
        top_a = max(a[sid], key=a[sid].get)
        if top_a != top_b:
            changed += 1
    return changed / total if total else 0.0


def spearman_vs_baseline(df, base_df) -> pd.Series:
    a, b = _ranked(df), _ranked(base_df)
    res = {}
    for sid in b:
        if sid not in a:
            continue
        depts = sorted(set(b[sid]) & set(a[sid]))
        if len(depts) < 2:
            continue
        res[sid] = _spearman([b[sid][d] for d in depts], [a[sid][d] for d in depts])
    return pd.Series(res)


def grade_migration(df, base_df) -> pd.DataFrame:
    a = df.set_index(["student_id", "department_id"])["grade"]
    b = base_df.set_index(["student_id", "department_id"])["grade"]
    j = pd.DataFrame({"base": b, "new": a}).dropna()
    return pd.crosstab(j["base"], j["new"])
