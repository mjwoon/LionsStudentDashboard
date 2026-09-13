"""RQ1 산출물 로더 — 후속 분석 스크립트들이 함께 쓴다.

SBERT 재계산 없이 `pairs_labeled.csv`(쌍별 sim·층·가중치)와 저장된 LLM 레이블만
읽는다. 둘 다 `experiment_rq1.py` 가 남긴다.
"""
from __future__ import annotations

import pandas as pd

from experiment.pairs import SampledPair

REQUIRED = {"pair_id", "i", "j", "sim", "bin_idx", "weight"}


def load_sample(pairs_csv: str) -> list[SampledPair]:
    df = pd.read_csv(pairs_csv)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise SystemExit(f"{pairs_csv}: 열 부족 {sorted(missing)}. "
                         "experiment_rq1.py 를 먼저 실행해 생성하세요.")
    return [SampledPair(int(r.pair_id), int(r.i), int(r.j),
                        float(r.sim), int(r.bin_idx), float(r.weight))
            for r in df.itertuples()]


def load_gold(results_dir: str) -> dict[int, int]:
    """gpt-4o 2회 독립 실행의 보수적 AND (= RQ1 골드)."""
    p1 = pd.read_csv(f"{results_dir}/llm_labels_pass1.csv").set_index("pair_id").label
    p2 = pd.read_csv(f"{results_dir}/llm_labels_pass2.csv").set_index("pair_id").label
    return {int(k): int(v) for k, v in ((p1 == 1) & (p2 == 1)).astype(int).items()}


def require_labels(sample, gold) -> None:
    missing = [sp.pair_id for sp in sample if sp.pair_id not in gold]
    if missing:
        raise SystemExit(f"레이블 없는 pair_id {len(missing)}건: {missing[:10]}")
