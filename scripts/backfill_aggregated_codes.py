#!/usr/bin/env python3
"""graphDB/course_all_aggregated.csv의 학수번호를 과목 마스터에서 보강한다.

왜 필요한가
-----------
유사도 실험(RQ1)은 교과목명·개요로 계산하므로 학수번호가 없어도 돌아간다. 그러나
RQ2가 쓰는 code→code lookup은 양쪽 모두 학수번호가 있는 쌍만 담는다
(graphDB/experiment/similarity_lookup.py). 채움률이 285/1,493(19.1%)이던 시점에는
유사도 0.7 이상인 쌍 115개 중 8개만 lookup에 들어갔다. 임계값 실험이 측정한 "영향이
작다"에 진짜 희소성과 학수번호 미기입이 섞여 있었다는 뜻이다.

과목 마스터(group3_courses.csv)가 1,519개로 재구축되면서 이름→코드 대응이 유일해졌다.
이 스크립트는 그 대응으로 비어 있는 학수번호만 채운다.

안전성
------
- 이름→코드가 유일한 경우만 채운다(마스터에 이름당 코드가 둘 이상인 경우 없음).
- 기존 값은 덮어쓰지 않는다. 실측 결과 기존 285건과 마스터 값의 불일치는 0건이다.
- 보강 후에도 중복 학수번호 행이 생기지 않으므로, 유효 쌍 규칙의 "같은 학수번호 쌍
  제외"가 달라지지 않는다. 즉 RQ1의 유효 쌍 모집단 1,113,585는 그대로다.
- 멱등하다. 다시 실행해도 결과가 같다.

사용법
------
    python3 scripts/backfill_aggregated_codes.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "graphDB" / "course_all_aggregated.csv"
MASTER = ROOT / "group3_courses.csv"


def _norm(name: str) -> str:
    """표기 차이를 흡수한 이름 키.

    마스터와 집계본이 같은 과목을 다르게 적는 경우가 있다. 대소문자
    ("AI리터러시" vs "Ai리터러시"), 로마 숫자("Ⅰ" vs "1"), 괄호·공백·중점이
    대표적이다. 수강 인원 상위 교양필수 세 과목이 이 차이만으로 코드를 얻지
    못하고 있었다.
    """
    s = str(name).strip().lower()
    for a, b in (("Ⅰ", "1"), ("Ⅱ", "2"), ("Ⅲ", "3")):
        s = s.replace(a.lower(), b)
    return re.sub(r"[\s()（）·ㆍ\-_/]", "", s)


def _unique_map(master: pd.DataFrame, key) -> dict:
    """이름 키 → 학수번호. 키가 코드 둘 이상에 걸리면 버린다."""
    keys = master["교과목이름"].map(key)
    codes = master["학수번호"].astype(str).str.strip()
    grouped = codes.groupby(keys)
    return {k: v.iloc[0] for k, v in grouped if v.nunique() == 1}


def main() -> int:
    agg = pd.read_csv(AGG)
    master = pd.read_csv(MASTER)

    exact = _unique_map(master, lambda s: str(s).strip())
    loose = _unique_map(master, _norm)

    before = int(agg["학수번호"].notna().sum())
    names = agg["교과목 이름"]

    # 정확한 이름 일치를 먼저 쓰고, 남은 것만 정규화 키로 채운다.
    agg["학수번호"] = agg["학수번호"].where(
        agg["학수번호"].notna(), names.astype(str).str.strip().map(exact)
    )
    filled_exact = int(agg["학수번호"].notna().sum())
    agg["학수번호"] = agg["학수번호"].where(
        agg["학수번호"].notna(), names.map(_norm).map(loose)
    )
    after = int(agg["학수번호"].notna().sum())
    print(f"  정확 일치 {filled_exact - before}건, 정규화 일치 {after - filled_exact}건")

    dup = int(agg["학수번호"].dropna().duplicated().sum())
    if dup:
        print(f"중단: 보강 후 중복 학수번호 {dup}건 — 유효 쌍 규칙이 달라진다", file=sys.stderr)
        return 1

    agg.to_csv(AGG, index=False)
    print(f"학수번호 보강: {before} → {after} / {len(agg)} ({100*after/len(agg):.1f}%)")
    print(f"마스터 매핑: 정확 {len(exact)}개 / 정규화 {len(loose)}개, 중복 코드 0건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
