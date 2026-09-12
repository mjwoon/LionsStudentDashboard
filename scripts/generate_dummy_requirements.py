#!/usr/bin/env python3
"""전공 진입요건·권장과목 더미 데이터 생성기.

왜 필요한가
-----------
group5_requirements_recs.csv에는 실제 학사 규정 기반 데이터가 13개 학과분만 있다.
평가 대상 38개 학과 중 34개에 진입요건이, 25개에 권장과목이 없어서 종합 적합도가
'교육과정 이수율' 한 항목으로만 계산되고, 학과끼리 기준이 달라 비교가 성립하지 않는다.
데모·개발 환경에서 3개 항목이 모두 살아있는 상태를 재현하기 위한 **합성 데이터**다.

    ⚠️  실제 학사 규정이 아니다. 운영 데이터로 쓰면 안 된다.
        모든 요건 설명에 '[더미]' 접두어가 붙는다.

생성 규칙 (결정론적 — 같은 입력이면 항상 같은 출력)
--------------------------------------------------
1. 대상: 평가 대상 학과(dept_id > 100) 중 라이언스 칼리지 계열(LIONS*) 제외.
   이미 실제 데이터가 있는 학과는 해당 항목을 건너뛴다(덮어쓰지 않는다).
2. 후보 과목 풀: 그 학과 1학년 '전공기초' → 없으면 '전공핵심'.
   교육과정이 아예 없는 세부전공(예: 신소재반도체공학전공)은 같은 단과대학에서
   dept_id가 바로 아래이면서 교육과정을 가진 학과(=모학부)의 과목을 차용한다.
3. 정렬: 실제 수강 이력 빈도 내림차순 → 동률은 학수번호 오름차순.
   아무도 듣지 않는 과목으로 요건을 채우면 전원 0점이 되어 변별력이 없어지므로,
   실제 요건이 그렇듯 학생들이 실제로 수강하는 기초과목을 우선한다.
4. 진입요건: 실제 ELEC 행의 관용구를 따른다 — 같은 후보 집합에 OR로 묶인 두 그룹.
   그룹1 = A(4.0) 이상 1과목, 그룹2 = B(3.0) 이상 2과목.
5. 권장과목: 같은 후보 풀 상위 3과목의 과목명.
6. 1학년 교육과정: 교육과정이 아예 없는 세부전공에는 모학부의 1학년 과목을 그대로
   복제한다. 세부전공은 실제로도 모학부의 1학년 과정을 공유하므로 임의 창작이 아니다.
   (설강학과는 모학부 이름을 유지하고 학과ID만 세부전공으로 바꾼다.)

사용법
------
    python3 scripts/generate_dummy_requirements.py

출력
----
    group5_requirements_recs_dummy.csv   요건·권장 더미 행만 (검토용)
    group5_requirements_recs_full.csv    요건·권장 실제 + 더미 (업로드용)
    group4_교육과정_full.csv              교육과정 실제 + 더미 (업로드용)
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPTS_CSV = ROOT / "group1_colleges_depts_.csv"
CURRICULUM_CSV = ROOT / "group4_교육과정_전체.csv"
REAL_CSV = ROOT / "group5_requirements_recs.csv"
ENROLLMENTS_CSV = ROOT / "sample_enrollments_300.csv"

DUMMY_OUT = ROOT / "group5_requirements_recs_dummy.csv"
FULL_OUT = ROOT / "group5_requirements_recs_full.csv"
CURRICULUM_FULL_OUT = ROOT / "group4_교육과정_full.csv"

HEADER = [
    "dept_code", "admission_year", "requirement_group", "target_grade_level",
    "required_count", "requirement_text", "is_alert_required", "logic_operator",
    "course_code", "recommended_course",
]

CURRICULUM_HEADER = ["학수번호", "교과목이름", "학점", "이수구분", "학년", "학기", "설강학과", "학과ID"]

# 라이언스 칼리지 계열 — 학생의 소속이지 '진입 대상 전공'이 아니다.
LIONS_CODES = {"LIONS1", "LIONS2", "LIONS3"}

ADMISSION_YEAR = "2026.0"
MAX_CANDIDATES = 5
MAX_RECOMMENDED = 3
DUMMY_PREFIX = "[더미]"


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_candidate_pools(curriculum, enrollment_counts):
    """학과ID -> 1학년 후보 과목 리스트(수강 빈도 내림차순)."""
    by_dept = defaultdict(list)
    for row in curriculum:
        if row["학년"] == "1":
            by_dept[row["학과ID"]].append(row)

    pools = {}
    for dept_id, rows in by_dept.items():
        for category in ("전공기초", "전공핵심"):
            picked = [r for r in rows if r["이수구분"] == category]
            if picked:
                break
        if not picked:
            continue
        picked.sort(key=lambda r: (-enrollment_counts.get(r["학수번호"], 0), r["학수번호"]))
        pools[dept_id] = picked
    return pools


def resolve_pool(dept, depts_by_college, pools):
    """학과의 후보 풀과, 차용한 경우 그 모학부.

    세부전공(예: 신소재반도체공학전공)은 교육과정이 별도로 등록돼 있지 않다.
    같은 단과대학에서 dept_id가 바로 아래이면서 교육과정을 가진 학과를 모학부로 본다.
    """
    own = pools.get(dept["dept_id"])
    if own:
        return own, None

    siblings = depts_by_college[dept["college_id"]]
    lower = [d for d in siblings if int(d["dept_id"]) < int(dept["dept_id"]) and pools.get(d["dept_id"])]
    if not lower:
        return None, None
    parent = max(lower, key=lambda d: int(d["dept_id"]))
    return pools[parent["dept_id"]], parent


def inherited_curriculum_rows(curriculum, parent, dept):
    """모학부의 1학년 교육과정을 세부전공 학과ID로 복제."""
    return [
        {**row, "학과ID": dept["dept_id"]}
        for row in curriculum
        if row["학과ID"] == parent["dept_id"] and row["학년"] == "1"
    ]


def requirement_rows(dept_code, candidates, borrowed_from):
    """ELEC 관용구 그대로: 같은 후보 집합에 OR로 묶인 두 그룹."""
    note = f" (교육과정 차용: {borrowed_from})" if borrowed_from else ""
    text = (
        f"{DUMMY_PREFIX} 아래 {len(candidates)}개 과목 중 "
        f"성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수{note}"
    )
    groups = [("1.0", "A", "1.0"), ("2.0", "B", str(min(2, len(candidates))) + ".0")]

    rows = []
    for group, grade, count in groups:
        for course in candidates:
            rows.append({
                "dept_code": dept_code,
                "admission_year": ADMISSION_YEAR,
                "requirement_group": group,
                "target_grade_level": grade,
                "required_count": count,
                "requirement_text": text,
                "is_alert_required": "True",
                "logic_operator": "AND",
                "course_code": course["학수번호"],
                "recommended_course": "",
            })
    return rows


def recommendation_rows(dept_code, candidates):
    return [
        {**{k: "" for k in HEADER}, "dept_code": dept_code, "recommended_course": c["교과목이름"]}
        for c in candidates[:MAX_RECOMMENDED]
    ]


def write_csv_with(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def write_csv(path, rows):
    write_csv_with(path, HEADER, rows)


def main():
    depts = read_csv(DEPTS_CSV)
    curriculum = read_csv(CURRICULUM_CSV)
    real_rows = read_csv(REAL_CSV)
    enrollments = read_csv(ENROLLMENTS_CSV)

    enrollment_counts = Counter(e["학수번호"] for e in enrollments)
    pools = build_candidate_pools(curriculum, enrollment_counts)

    depts_by_college = defaultdict(list)
    for d in depts:
        depts_by_college[d["college_id"]].append(d)

    has_requirement = {r["dept_code"] for r in real_rows if r["requirement_group"]}
    has_recommendation = {r["dept_code"] for r in real_rows if r["recommended_course"]}

    targets = [
        d for d in depts
        if int(d["dept_id"]) > 100 and d["dept_code"] not in LIONS_CODES
    ]
    targets.sort(key=lambda d: int(d["dept_id"]))

    dummy_rows, curriculum_dummy, skipped, inherited = [], [], [], []
    req_added = rec_added = 0

    for dept in targets:
        code = dept["dept_code"]
        pool, parent = resolve_pool(dept, depts_by_college, pools)
        if not pool:
            skipped.append(dept["dept_name"])
            continue

        candidates = pool[:MAX_CANDIDATES]
        if code not in has_requirement:
            dummy_rows.extend(requirement_rows(code, candidates, parent["dept_name"] if parent else None))
            req_added += 1
        if code not in has_recommendation:
            dummy_rows.extend(recommendation_rows(code, candidates))
            rec_added += 1

        # 교육과정이 없는 세부전공에는 모학부의 1학년 과정을 물려준다.
        if parent is not None:
            rows = inherited_curriculum_rows(curriculum, parent, dept)
            if rows:
                curriculum_dummy.extend(rows)
                inherited.append(f'{dept["dept_name"]}<-{parent["dept_name"]}')

    write_csv(DUMMY_OUT, dummy_rows)
    write_csv(FULL_OUT, [{k: r.get(k, "") for k in HEADER} for r in real_rows] + dummy_rows)
    write_csv_with(
        CURRICULUM_FULL_OUT,
        CURRICULUM_HEADER,
        [{k: r.get(k, "") for k in CURRICULUM_HEADER} for r in curriculum] + curriculum_dummy,
    )

    print(f"평가 대상 학과       : {len(targets)}개")
    print(f"진입요건 더미 생성   : {req_added}개 학과")
    print(f"권장과목 더미 생성   : {rec_added}개 학과")
    print(f"후보 과목 없어 제외  : {len(skipped)}개 학과 {skipped if skipped else ''}")
    print(f"교육과정 상속        : {len(inherited)}개 학과 {inherited if inherited else ''}")
    print(f"더미 행              : {len(dummy_rows)}행 -> {DUMMY_OUT.name}")
    print(f"통합(실제+더미)      : {len(real_rows) + len(dummy_rows)}행 -> {FULL_OUT.name}")
    print(f"교육과정 통합        : {len(curriculum) + len(curriculum_dummy)}행 -> {CURRICULUM_FULL_OUT.name}")


if __name__ == "__main__":
    main()
