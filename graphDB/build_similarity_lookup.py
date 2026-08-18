"""graphDB(3.11) 환경 전용: 하이브리드 유사도 → code→code lookup 을 디스크로 덤프.

RQ2 평가는 루트 3.12 환경에서 이 덤프를 로드해 sbert 없이 재계산한다.
"""
from __future__ import annotations

import argparse
import os

from similarity_engine import load_course_data
from experiment.pairs import compute_hybrid_similarity
from experiment.similarity_lookup import build_lookup, save_lookup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="course_all_aggregated.csv")
    ap.add_argument("--out", default="results/rq2/similarity_lookup.json")
    ap.add_argument("--min-keep", type=float, default=0.6)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df = load_course_data(args.csv)
    sim = compute_hybrid_similarity(df)
    lut = build_lookup(df, sim, min_keep=args.min_keep)
    save_lookup(lut, args.out)
    print(f"lookup 저장: {args.out} ({len(lut)} pairs, min_keep={args.min_keep})")


if __name__ == "__main__":
    main()
