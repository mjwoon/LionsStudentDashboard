#!/usr/bin/env python3
"""과목 마스터(group3_courses.csv) 재구축 — 학수번호를 원천에서 되찾는다.

왜 필요한가
-----------
group3_courses.csv에는 과목이 318개뿐이었다. 교육과정(group4)이 참조하는 학수번호
65개가 마스터에 없어 requirement_courses의 외래키를 걸 수 없었고, 그 탓에 디자인대학
4개 학과는 진입요건을 만들 수조차 없었다.

추적해보니 과목이 없는 게 아니라 **학수번호가 없었다**. 계보는 이렇다.

    2024_1to2025_1_smr.csv   개설 강좌 원천. 학수번호 1,511개.
    course_all.xlsx          과목 카탈로그 1,493개. 교과목개요 100%. 학수번호 컬럼 없음.
        ├─→ group3_courses.csv            그중 318개만 코드를 붙인 부분집합
        ├─→ graphDB/course_all_aggregated group3에서 코드를 역보강 → 19%만 채워짐
        └─→ group4_교육과정_전체            별도 경로. 코드 140개.

group3와 group4는 파생 관계가 아니라 각각 따로 만들어진 부분집합이라 코드가 어긋나 있었다.

무엇을 합치나
-------------
1. course_all(이름·학점·이수구분·학년·설강학과·개요) × smr(학수번호)을 과목명으로 조인.
   smr에서 이름이 여러 코드로 갈리는 과목은 어느 쪽인지 단정할 수 없으므로 버린다.
2. group4에만 있는 과목은 group4 값으로 채운다. 교과목개요가 없지만, 없는 것보다
   낫다 — 마스터에 없으면 외래키 때문에 요건 자체를 만들 수 없다.
3. 기존 group3에만 있던 과목도 유지한다. 수강 이력·요건이 이미 참조하고 있을 수 있다.

중복 학수번호는 먼저 채택한 출처를 남긴다(우선순위: 기존 group3 > course_all+smr > group4).
기존 항목을 이기지 않게 해서, 이미 쓰이던 과목의 값이 조용히 바뀌는 일을 막는다.

사용법:  python3 scripts/rebuild_course_master.py [--dry-run]
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS = Path.home() / "Downloads"

MASTER = ROOT / "group3_courses.csv"
CURRICULUM = ROOT / "group4_교육과정_전체.csv"
CATALOG = DOWNLOADS / "course_all.xlsx - course_all.csv"
OFFERINGS = DOWNLOADS / "2024_1to2025_1_smr (1).csv"

HEADER = ["학수번호", "교과목이름", "학점", "이수구분", "학년", "학기",
          "설강학과", "교과목개요", "교육과정학과코드"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def norm(s):
    """과목명 대조용 정규화. 파일마다 공백·기호 표기가 달라 그대로는 안 맞는다."""
    return re.sub(r"[\s·&/()\-:]", "", (s or "")).lower()


def build_code_lookup(offerings):
    """과목명 -> 학수번호. 한 이름이 여러 코드로 갈리면 제외한다(오배정 방지)."""
    by_name = defaultdict(set)
    for row in offerings:
        code = (row.get("학수번호") or "").strip()
        if code:
            by_name[norm(row.get("교과목 이름"))].add(code)
    return {name: next(iter(codes)) for name, codes in by_name.items() if len(codes) == 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="쓰지 않고 집계만 출력")
    args = ap.parse_args()

    for p in (CATALOG, OFFERINGS):
        if not p.exists():
            raise SystemExit(f"원천 파일이 없습니다: {p}")

    existing = read_csv(MASTER)
    curriculum = read_csv(CURRICULUM)
    catalog = read_csv(CATALOG)
    code_of = build_code_lookup(read_csv(OFFERINGS))

    out = {}          # 학수번호 -> row
    origin = {}       # 학수번호 -> 출처(집계용)

    def put(code, row, src):
        if not code or code in out:
            return False
        out[code] = {k: row.get(k, "") for k in HEADER}
        out[code]["학수번호"] = code
        origin[code] = src
        return True

    # 1) 기존 마스터가 최우선. 이미 참조되고 있는 값을 바꾸지 않는다.
    for r in existing:
        put(r["학수번호"], r, "기존 group3")

    # 2) 카탈로그 × 개설강좌
    for r in catalog:
        code = code_of.get(norm(r["교과목 이름"]))
        put(code, {
            "교과목이름": r["교과목 이름"], "학점": "", "이수구분": r.get("이수구분", ""),
            "학년": r.get("학년", ""), "학기": "", "설강학과": r.get("설강학과", ""),
            "교과목개요": r.get("교과목개요", ""), "교육과정학과코드": "",
        }, "course_all+smr")

    # 3) 교육과정에만 있는 과목 — 개요는 없지만 마스터에 있어야 요건을 걸 수 있다.
    for r in curriculum:
        put(r["학수번호"], {
            "교과목이름": r["교과목이름"], "학점": r.get("학점", ""),
            "이수구분": r.get("이수구분", ""), "학년": r.get("학년", ""),
            "학기": r.get("학기", ""), "설강학과": r.get("설강학과", ""),
            "교과목개요": "", "교육과정학과코드": "",
        }, "group4")

    rows = [out[c] for c in sorted(out)]
    counts = defaultdict(int)
    for c in out:
        counts[origin[c]] += 1

    print(f"기존 마스터        {len({r['학수번호'] for r in existing})}개")
    for src in ("기존 group3", "course_all+smr", "group4"):
        print(f"  {src:<16} {counts[src]:>5}개")
    print(f"재구축 결과        {len(rows)}개 과목")
    filled = sum(1 for r in rows if (r["교과목개요"] or "").strip())
    print(f"  교과목개요 있음   {filled}/{len(rows)} ({filled/len(rows)*100:.0f}%)")

    if args.dry_run:
        print("\n--dry-run: 파일을 쓰지 않았습니다.")
        return

    with open(MASTER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print(f"\n-> {MASTER.name}")


if __name__ == "__main__":
    main()
