#!/usr/bin/env python3
"""평가 파이프라인 종단 검증 — 실제 업로드 API로 시딩하고 실제 평가 API를 단정한다.

단위 테스트는 함수를 부르고, 이 스크립트는 **앱을 부른다**. CSV를 실제 업로드
엔드포인트로 넣고 평가 엔드포인트 응답을 확인하므로 DB 방언·직렬화·라우터 배선까지
한 번에 걸린다. SQLite에서만 확인하고 끝내면 Postgres에서 처음 드러나는 문제
(Numeric에 None, JSON 안의 null, 한글 콜레이션)를 놓친다.

사용법:
    # 1) 백엔드를 원하는 DATABASE_URL로 띄운다
    DATABASE_URL=postgresql+psycopg://user:password@localhost:55433/my_db \
      uv run uvicorn main:app --port 8199

    # 2) 검증
    python3 scripts/verify_evaluation_e2e.py --base-url http://127.0.0.1:8199

종료 코드 0 = 전부 통과.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (엔드포인트, CSV) — 순서가 곧 의존 관계다. 학과가 없으면 요건이 붙지 못한다.
SEED_PLAN = [
    ("org", "group1_colleges_depts_.csv"),
    ("courses", "group3_courses.csv"),
    ("curriculum", "group4_교육과정_전체.csv"),
    ("requirements", "group5_requirements_recs.csv"),
    ("students", "sample_students_300.csv"),
    ("enrollments", "sample_enrollments_300.csv"),
]

# 라이언스 칼리지 계열 — 학생의 소속이지 진입 대상 전공이 아니다.
LIONS_TRACKS = {"전계열", "인문사회계열", "자연계열"}

SPARSE_STUDENT = 2026105814   # 배지민 — 성적 있는 과목 4개뿐
ICT_DATA_DEPT = 303           # 데이터인텔리전스전공


class Checker:
    def __init__(self):
        self.failures = []

    def check(self, ok, msg):
        print(f"  {'PASS' if ok else 'FAIL'}  {msg}")
        if not ok:
            self.failures.append(msg)

    def report(self):
        if self.failures:
            print(f"\n결과: {len(self.failures)}건 실패")
            for f in self.failures:
                print(f"  - {f}")
            return 1
        print("\n결과: 전부 통과")
        return 0


def post_file(base, endpoint, path):
    """multipart/form-data 업로드 (표준 라이브러리만 사용)."""
    boundary = "----lionsverify"
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{path.name}"\r\nContent-Type: text/csv\r\n\r\n'.encode(),
        path.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"{base}/api/admin/upload-grouped/{endpoint}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def get(base, path, timeout=900):
    with urllib.request.urlopen(f"{base}{path}", timeout=timeout) as r:
        return json.load(r)


def seed(base, c):
    print("\n[시딩] 실제 업로드 API")
    for endpoint, filename in SEED_PLAN:
        resp = post_file(base, endpoint, ROOT / filename)
        skipped = sum(
            s.get("skipped_count", 0) for s in (resp.get("sub_results") or [])
        )
        detail = f" (건너뛴 행 {skipped})" if skipped else ""
        c.check(resp.get("success") is True and skipped == 0,
                f"{endpoint} 업로드 성공{detail}")


def verify_department_scope(base, c):
    print("\n[1] 평가 대상 학과 범위")
    everything = get(base, "/api/departments")
    targets = get(base, "/api/departments?evaluation_targets_only=true")

    all_names = {d["name"] for d in everything["departments"]}
    target_names = {d["name"] for d in targets["departments"]}

    c.check(LIONS_TRACKS <= all_names, "기본 목록은 라이언스 계열을 그대로 반환한다")
    c.check(not (LIONS_TRACKS & target_names), "평가 대상에는 라이언스 계열이 없다")
    c.check(len(target_names) == len(all_names) - len(LIONS_TRACKS),
            f"평가 대상 = 전체 - 3 ({len(target_names)} = {len(all_names)} - 3)")


def verify_no_vacuous_full_marks(base, c):
    print("\n[2] 데이터 공백이 만점이 되지 않는다")
    r = get(base, f"/api/evaluation/student/{SPARSE_STUDENT}/department/{ICT_DATA_DEPT}"
                  "?force_recalculate=true", timeout=120)
    overall = r["analysis_json"]["overall"]

    c.check(r["is_evaluable"] is True, "평가 가능 학과로 판정된다")
    c.check(len(overall["scored_components"]) == 3, "세 항목이 모두 반영된다")
    c.check(r["overall_score"] < 70,
            f"요건 미충족 학생이 70점 미만이다 (실제 {r['overall_score']})")
    c.check(r["entry_gate"] == "blocked", "진입요건 관문이 blocked다")
    c.check(r["grade"] is None, "관문을 못 넘으면 등급을 주지 않는다")


def verify_gate_dominates_ranking(base, c):
    print("\n[3] 진입요건 관문이 학과 추천 순위를 지배한다")
    data = get(base, f"/api/evaluation/student/{SPARSE_STUDENT}/all-departments")
    results = data["results"]
    names = [r["department_name"] for r in results]

    c.check(not (LIONS_TRACKS & set(names)), "추천 목록에 라이언스 계열이 없다")

    order = {"open": 2, "unknown": 1, "blocked": 0}
    gates = [order.get(r.get("entry_gate", "unknown"), 0)
             for r in results if r.get("is_evaluable", True)]
    c.check(gates == sorted(gates, reverse=True),
            "요건 충족 학과가 미충족 학과보다 항상 위에 온다")

    graded = [r for r in results if r.get("grade") is not None]
    c.check(all(r.get("entry_gate") != "blocked" for r in graded),
            "등급이 붙은 학과 중 요건 미충족은 없다")


def verify_null_score_roundtrip(base, c):
    """평가 불가 학과는 overall_score=None으로 저장·재조회되어야 한다.

    Numeric 컬럼에 NULL을 쓰는 경로라 DB 방언에 따라 처음 깨질 수 있다.
    """
    print("\n[4] 평가 불가 학과의 NULL 점수 왕복")
    data = get(base, f"/api/evaluation/student/{SPARSE_STUDENT}/all-departments")
    blanks = [r for r in data["results"] if not r.get("is_evaluable", True)]
    if not blanks:
        print("  SKIP  평가 불가 학과가 없다(요건 데이터가 모두 채워진 상태)")
        return
    c.check(all(r["overall_score"] is None for r in blanks),
            "평가 불가 학과는 점수가 None이다")
    c.check(all(r["grade"] is None for r in blanks), "등급도 None이다")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8199")
    ap.add_argument("--skip-seed", action="store_true",
                    help="이미 시딩된 DB에 대해 단정만 수행")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    c = Checker()
    try:
        if not args.skip_seed:
            seed(base, c)
        verify_department_scope(base, c)
        verify_no_vacuous_full_marks(base, c)
        verify_gate_dominates_ranking(base, c)
        verify_null_score_roundtrip(base, c)
    except urllib.error.URLError as e:
        print(f"\n서버에 연결할 수 없다 ({base}): {e}")
        return 2
    return c.report()


if __name__ == "__main__":
    sys.exit(main())
