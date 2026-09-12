#!/usr/bin/env python3
"""전공 진입요건·권장과목 더미 데이터 생성기.

왜 필요한가
-----------
저장소의 요건 데이터는 원래 4개 학과분 진입요건, 13개 학과분 권장과목뿐이었다.
평가 대상 38개 학과 중 나머지는 종합 적합도가 '교육과정 이수율' 한 항목으로만
계산되고, 학과끼리 기준이 달라 비교가 성립하지 않는다. 개발·실험 환경에서 3개 항목이
모두 살아있는 상태를 재현하기 위한 **합성 데이터**다.

    ⚠️  실제 학사 규정이 아니다. 다만 데이터 자체에는 표식을 남기지 않는다.
        어느 학과에 생성했는지는 .generated-requirements.json 대장에만 적힌다.

원본 CSV에 제자리(in-place)로 병합한다. 재실행하면 대장에 적힌 학과의 이전 생성분을
먼저 걷어내고 다시 만들므로 몇 번을 돌려도 결과가 같다(중복이 쌓이지 않는다).
대장을 지우면 걷어낼 근거가 사라져 행이 누적되니 함께 관리해야 한다.

생성 규칙 (결정론적 — 같은 입력이면 항상 같은 출력)
--------------------------------------------------
1. 대상: 평가 대상 학과(dept_id > 100) 중 라이언스 칼리지 계열(LIONS*) 제외.
   원본('[더미]'가 아닌 행)에 이미 데이터가 있는 학과는 그 항목을 건너뛴다.
2. 후보 과목 풀: 그 학과 1학년 '전공기초' → 없으면 '전공핵심'.
   교육과정이 아예 없는 세부전공(예: 신소재반도체공학전공)은 같은 단과대학에서
   dept_id가 바로 아래이면서 교육과정을 가진 학과(=모학부)의 과목을 차용한다.
3. 후보는 반드시 **과목 마스터(group3)** 에 있는 학수번호여야 한다.
   requirement_courses.course_code가 courses를 참조하는 외래키라, 교육과정(group4)에만
   있고 마스터에 없는 코드를 쓰면 Postgres에서 외래키 위반으로 업로드가 통째로 깨진다
   (SQLite는 외래키를 강제하지 않아 이 문제를 숨긴다).
4. 정렬: 실제 수강 이력 빈도 내림차순 → 동률은 학수번호 오름차순.
   아무도 듣지 않는 과목으로 요건을 채우면 전원 0점이 되어 변별력이 없어지므로,
   실제 요건이 그렇듯 학생들이 실제로 수강하는 기초과목을 우선한다.
5. 진입요건: 실제 ELEC 행의 관용구를 따른다 — 같은 후보 집합에 OR로 묶인 두 그룹.
   그룹1 = A(4.0) 이상 1과목, 그룹2 = B(3.0) 이상 2과목.
6. 권장과목: 같은 후보 풀 상위 3과목의 과목명.
7. 1학년 교육과정: 교육과정 행이 **아예 없는** 세부전공에만 모학부의 1학년 과목을
   복제한다. 세부전공은 실제로도 모학부의 1학년 과정을 공유하므로 임의 창작이 아니다.
   (설강학과는 모학부 이름을 유지하고 학과ID만 세부전공으로 바꾼다.)
   '교육과정은 있는데 과목 마스터에 없어 후보가 비는' 경우는 이와 다른 상황이므로
   교육과정을 물려주지 않는다 — 남의 학과 과목을 제 것으로 만들어버리게 된다.

사용법
------
    python3 scripts/generate_dummy_requirements.py

갱신 대상 (제자리 병합)
----------------------
    group5_requirements_recs.csv   진입요건 + 권장과목
    group4_교육과정_전체.csv        1학년 교육과정 (상속분 추가)
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPTS_CSV = ROOT / "group1_colleges_depts_.csv"
CURRICULUM_CSV = ROOT / "group4_교육과정_전체.csv"
REAL_CSV = ROOT / "group5_requirements_recs.csv"
ENROLLMENTS_CSV = ROOT / "sample_enrollments_300.csv"
COURSES_CSV = ROOT / "group3_courses.csv"  # 과목 마스터 — 요건 과목의 외래키 대상

# 제자리 병합 — 별도 산출물을 두지 않는다. 파일이 둘이면 업로드할 때 어느 쪽이
# 맞는지 매번 헷갈리고, seeding 스크립트마다 파일명을 바꿔야 한다.
REQUIREMENTS_OUT = REAL_CSV
CURRICULUM_OUT = CURRICULUM_CSV

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
# 생성분을 어느 학과에 만들었는지 기록하는 대장. requirement_text에 표식을 넣지
# 않기로 했으므로(데이터에 '더미' 같은 단어를 남기지 않는다), 재실행 시 이전 생성분을
# 걷어내는 근거가 이 파일뿐이다. 지우면 다음 실행에서 행이 중복 누적된다.
MANIFEST = ROOT / ".generated-requirements.json"


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_candidate_pools(curriculum, enrollment_counts, master_codes):
    """학과ID -> 1학년 후보 과목 리스트(수강 빈도 내림차순).

    master_codes에 없는 학수번호는 후보에서 뺀다. requirement_courses가 courses를
    참조하는 외래키라, 교육과정에만 있는 코드를 넣으면 Postgres에서 업로드 전체가
    외래키 위반으로 롤백된다.
    """
    by_dept = defaultdict(list)
    for row in curriculum:
        if row["학년"] == "1" and row["학수번호"] in master_codes:
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


def find_parent(dept, depts_by_college, pools):
    """같은 단과대학에서 dept_id가 바로 아래이면서 후보 풀을 가진 학과(=모학부)."""
    siblings = depts_by_college[dept["college_id"]]
    lower = [
        d for d in siblings
        if int(d["dept_id"]) < int(dept["dept_id"]) and pools.get(d["dept_id"])
    ]
    return max(lower, key=lambda d: int(d["dept_id"])) if lower else None


def inherited_curriculum_rows(curriculum, parent, dept):
    """모학부의 1학년 교육과정을 세부전공 학과ID로 복제."""
    return [
        {**row, "학과ID": dept["dept_id"]}
        for row in curriculum
        if row["학과ID"] == parent["dept_id"] and row["학년"] == "1"
    ]


def requirement_rows(dept_code, candidates):
    """ELEC 관용구 그대로: 같은 후보 집합에 OR로 묶인 두 그룹.

    모학부에서 차용했다는 주석은 넣지 않는다. 1회차에 교육과정이 상속되고 나면
    2회차에는 그 학과가 제 교육과정을 갖게 되어 '차용'이 아니게 되고, 그러면
    requirement_text가 실행 횟수에 따라 달라져 멱등성이 깨진다.
    상속 관계는 교육과정 파일(설강학과=모학부, 학과ID=세부전공)과 실행 로그에 남는다.
    """
    text = (
        f"아래 {len(candidates)}개 과목 중 "
        f"성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수"
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


def load_manifest():
    """직전 실행이 어느 학과에 무엇을 생성했는지."""
    if not MANIFEST.exists():
        return {"requirement_dept_codes": [], "recommendation_dept_codes": []}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def strip_previous_output(rows, manifest):
    """대장에 적힌 학과의 생성분을 걷어낸다 — 재실행해도 중복이 쌓이지 않게.

    데이터에 표식을 남기지 않으므로 대장이 유일한 근거다. 대장이 없거나 지워졌으면
    아무것도 걷어내지 못하고 그대로 누적된다.
    """
    req = set(manifest.get("requirement_dept_codes", []))
    rec = set(manifest.get("recommendation_dept_codes", []))
    kept = []
    for r in rows:
        if r["requirement_group"] and r["dept_code"] in req:
            continue
        if r["recommended_course"] and r["dept_code"] in rec:
            continue
        kept.append(r)
    return kept


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
    enrollments = read_csv(ENROLLMENTS_CSV)

    # 이전에 만든 행을 대장 기준으로 걷어내고 원본만 남긴다 → 몇 번을 돌려도 결과가 같다.
    existing_rows = read_csv(REAL_CSV)
    real_rows = strip_previous_output(existing_rows, load_manifest())
    regenerated = len(existing_rows) - len(real_rows)

    enrollment_counts = Counter(e["학수번호"] for e in enrollments)
    master_codes = {c["학수번호"] for c in read_csv(COURSES_CSV)}
    pools = build_candidate_pools(curriculum, enrollment_counts, master_codes)

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

    # 교육과정 행이 아예 없는 학과 — 이 학과들만 모학부 과정을 물려받을 자격이 있다.
    depts_without_curriculum = {
        row_dept_id
        for row_dept_id in {d["dept_id"] for d in targets}
        if not any(c["학과ID"] == row_dept_id and c["학년"] == "1" for c in curriculum)
    }

    for dept in targets:
        code = dept["dept_code"]
        own_pool = pools.get(dept["dept_id"])
        parent = None if own_pool else find_parent(dept, depts_by_college, pools)

        # 교육과정이 통째로 없는 세부전공에만 모학부 1학년 과정을 복제한다.
        if parent is not None and dept["dept_id"] in depts_without_curriculum:
            rows = inherited_curriculum_rows(curriculum, parent, dept)
            if rows:
                curriculum_dummy.extend(rows)
                inherited.append(f'{dept["dept_name"]}<-{parent["dept_name"]}')

        pool = own_pool or (pools.get(parent["dept_id"]) if parent else None)
        if not pool:
            # 1학년 과목이 과목 마스터(group3)에 하나도 없는 학과. 요건 후보를 만들 수
            # 없다 — 없는 과목으로 요건을 채우면 외래키 위반이거나 영원히 미충족이 된다.
            skipped.append(dept["dept_name"])
            continue

        candidates = pool[:MAX_CANDIDATES]
        if code not in has_requirement:
            dummy_rows.extend(requirement_rows(code, candidates))
            req_added += 1
        if code not in has_recommendation:
            dummy_rows.extend(recommendation_rows(code, candidates))
            rec_added += 1

    write_csv(REQUIREMENTS_OUT, [{k: r.get(k, "") for k in HEADER} for r in real_rows] + dummy_rows)
    # 다음 실행이 이번 생성분을 걷어낼 수 있도록 대장을 갱신한다.
    MANIFEST.write_text(
        json.dumps(
            {
                "requirement_dept_codes": sorted({r["dept_code"] for r in dummy_rows if r["requirement_group"]}),
                "recommendation_dept_codes": sorted({r["dept_code"] for r in dummy_rows if r["recommended_course"]}),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_csv_with(
        CURRICULUM_OUT,
        CURRICULUM_HEADER,
        [{k: r.get(k, "") for k in CURRICULUM_HEADER} for r in curriculum] + curriculum_dummy,
    )

    print(f"평가 대상 학과       : {len(targets)}개")
    print(f"진입요건 더미 생성   : {req_added}개 학과")
    print(f"권장과목 더미 생성   : {rec_added}개 학과")
    print(f"후보 과목 없어 제외  : {len(skipped)}개 학과 {skipped if skipped else ''}")
    print(f"교육과정 상속        : {len(inherited)}개 학과 {inherited if inherited else ''}")
    if regenerated:
        print(f"이전 생성분 교체     : {regenerated}행 제거 후 재생성")
    print(f"원본(비-더미) 행     : {len(real_rows)}행")
    print(f"생성 행              : {len(dummy_rows)}행")
    print(f"요건 파일            : {len(real_rows) + len(dummy_rows)}행 -> {REQUIREMENTS_OUT.name}")
    print(f"교육과정 파일        : {len(curriculum) + len(curriculum_dummy)}행 -> {CURRICULUM_OUT.name}")


if __name__ == "__main__":
    main()
