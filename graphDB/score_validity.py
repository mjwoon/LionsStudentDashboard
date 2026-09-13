"""사람 레이블 ↔ LLM 골드 타당성(validity) 채점.

RQ1 의 정답지는 gpt-4o 2회 독립 실행의 보수적 AND 로 만든 'LLM 보조 레이블'이다.
두 실행 간 κ=0.859 는 자기일관성(reliability)이며 타당성(validity)이 아니다
(Norman et al. 2026, "Reliability without Validity").

이 스크립트는 사람이 채운 채점표를 받아 LLM 골드와의 κ 를 계산한다.
t* 를 실제로 결정하는 것은 유사도 ≥0.7 구간(pair_id 220~334, 115쌍)이므로
기본값은 그 부분집합만 요구한다.

사용법:
    python score_validity.py --human results/rq1/validity_sheet_top115_filled.csv
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from experiment.kappa import cohen_kappa, confusion_2x2

TOP_BAND_START = 220  # 유사도 >=0.7 구간 시작 pair_id (strata: 100/60/60/64/34/17)


def _load_labels(path: str, col: str = "label") -> pd.Series:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "pair_id" not in df.columns or col not in df.columns:
        raise SystemExit(f"{path}: 'pair_id' 와 '{col}' 열이 필요합니다.")
    s = df.set_index("pair_id")[col]
    s = pd.to_numeric(s, errors="coerce")
    if s.isna().any():
        missing = s[s.isna()].index.tolist()
        raise SystemExit(f"{path}: 비어 있거나 숫자가 아닌 레이블 {len(missing)}건 (pair_id {missing[:10]}...)")
    bad = set(s.unique()) - {0, 1}
    if bad:
        raise SystemExit(f"{path}: 레이블은 0/1 이어야 합니다. 발견된 값: {sorted(bad)}")
    return s.astype(int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human", required=True, help="사람이 채운 채점표 CSV (pair_id,label)")
    ap.add_argument("--results", default="results/rq1", help="RQ1 산출물 디렉터리")
    ap.add_argument("--out", default=None, help="결과 JSON 경로 (기본: <results>/validity.json)")
    args = ap.parse_args()
    out = args.out or f"{args.results}/validity.json"

    human = _load_labels(args.human)
    p1 = _load_labels(f"{args.results}/llm_labels_pass1.csv")
    p2 = _load_labels(f"{args.results}/llm_labels_pass2.csv")
    gold = ((p1 == 1) & (p2 == 1)).astype(int)

    ids = sorted(set(human.index) & set(gold.index))
    if not ids:
        raise SystemExit("사람 레이블과 LLM 레이블의 pair_id 가 겹치지 않습니다.")
    h = [int(human[i]) for i in ids]
    g = [int(gold[i]) for i in ids]

    top = [i for i in ids if i >= TOP_BAND_START]
    res = {
        "n_compared": len(ids),
        "n_top_band": len(top),
        "coverage_note": f"pair_id >= {TOP_BAND_START} 는 유사도 >=0.7 구간(t* 결정 구간)",
        "human_positives": sum(h),
        "llm_gold_positives": sum(g),
        "validity_kappa_human_vs_llm_gold": cohen_kappa(h, g),
        "confusion_human_vs_llm_gold": confusion_2x2(h, g),
        "validity_kappa_human_vs_llm_pass1": cohen_kappa(h, [int(p1[i]) for i in ids]),
        "validity_kappa_human_vs_llm_pass2": cohen_kappa(h, [int(p2[i]) for i in ids]),
    }
    if top:
        ht = [int(human[i]) for i in top]
        gt = [int(gold[i]) for i in top]
        res["top_band_kappa"] = cohen_kappa(ht, gt)
        res["top_band_confusion"] = confusion_2x2(ht, gt)

    json.dump(res, open(out, "w"), ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
