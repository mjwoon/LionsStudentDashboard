"""
course_all_aggregated.csv 에 group3_courses.csv 의 '학점'·'학수번호' 를 보강.

aggregated 를 정본으로 유지하되, 정규화 데이터(group3)에서 학점/학수번호를 조인해
채운다. 매칭 전략:
  1) (정규화 과목명, 설강학과) 정확 일치
  2) group3 내에서 과목명이 유일한 경우에 한해 과목명 단독 보조 매칭
미매칭 행은 학수번호="" / 학점=빈값 → 기존 파이프라인이 credits 를 '학년'으로 폴백한다.

주의: group3 과목명 컬럼은 '교과목이름'(공백 없음), aggregated 는 '교과목 이름'(공백 있음).
"""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

Lookup = Dict[Tuple[str, str], Tuple[str, object]]
NameLookup = Dict[str, Tuple[str, object]]


def _norm(s: object) -> str:
    return str(s).strip().replace(" ", "")


def build_group3_lookup(g3: pd.DataFrame) -> tuple[Lookup, NameLookup]:
    """group3 에서 (이름,학과)→(코드,학점) 과 유일이름→(코드,학점) 룩업 생성."""
    name_counts = g3["교과목이름"].map(_norm).value_counts()

    pair: Lookup = {}
    name_lookup: NameLookup = {}
    for _, r in g3.iterrows():
        nm = _norm(r["교과목이름"])
        dept = str(r["설강학과"]).strip()
        value = (str(r["학수번호"]).strip(), r["학점"])
        pair.setdefault((nm, dept), value)
        if name_counts[nm] == 1:
            name_lookup.setdefault(nm, value)
    return pair, name_lookup


def enrich(agg: pd.DataFrame, g3: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """aggregated 에 '학수번호'·'학점' 컬럼을 채워 반환. (df, 매칭 통계) 튜플."""
    pair, name_lookup = build_group3_lookup(g3)

    codes: list = []
    credits: list = []
    n_pair = n_name = n_miss = 0

    for _, r in agg.iterrows():
        nm = _norm(r["교과목 이름"])
        dept = str(r["설강학과"]).strip()
        if (nm, dept) in pair:
            code, credit = pair[(nm, dept)]
            n_pair += 1
        elif nm in name_lookup:
            code, credit = name_lookup[nm]
            n_name += 1
        else:
            code, credit = "", ""  # 미매칭 → 빈 값(학점은 폴백 대상)
            n_miss += 1
        codes.append(code if str(code).strip() else "")
        credits.append("" if credit == "" or pd.isna(credit) else int(credit))

    out = agg.copy()
    out["학수번호"] = codes
    out["학점"] = credits
    stats = {
        "total": len(agg),
        "matched_pair": n_pair,
        "matched_name": n_name,
        "unmatched": n_miss,
    }
    return out, stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="aggregated CSV 에 학점/학수번호 보강")
    parser.add_argument("--aggregated", default="course_all_aggregated.csv")
    parser.add_argument("--group3", default="../group3_courses.csv")
    parser.add_argument("--out", default=None,
                        help="출력 경로(기본: aggregated 파일에 덮어쓰기)")
    args = parser.parse_args()

    agg = pd.read_csv(args.aggregated, encoding="utf-8-sig")
    g3 = pd.read_csv(args.group3, encoding="utf-8-sig")
    out, stats = enrich(agg, g3)

    out_path = args.out or args.aggregated
    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    logger.info("보강 완료 → %s", out_path)
    logger.info("  전체 %d행 | (이름+학과) %d | (유일이름) %d | 미매칭 %d (%.1f%%)",
                stats["total"], stats["matched_pair"], stats["matched_name"],
                stats["unmatched"], stats["unmatched"] / stats["total"] * 100)


if __name__ == "__main__":
    main()
