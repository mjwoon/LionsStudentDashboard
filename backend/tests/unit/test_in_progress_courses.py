"""'듣는 중' 과목(성적 미산출)의 채점 규칙.

2학기 수강 이력은 성적이 아직 없다. 예전에는 이런 행을 '수강하지 않음'과 똑같이
버려서 학생이 실제로 들은 과목의 절반가량이 평가에서 사라졌다. 지금은 별도 상태로
구분해, 성적이 판정 기준인 진입요건에서는 빼고 이수율에는 넣는다.
"""

from lions_core import scoring
from lions_core.scoring import SimilarMatch


def _detail(code, name, numeric, in_progress=False):
    return {
        "course_code": code,
        "course_name": name,
        "grade": "" if in_progress else "A",
        "credits": 3,
        "numeric_grade": numeric,
        "in_progress": in_progress,
    }


def _completed(details):
    return {
        "codes": {d["course_code"] for d in details},
        "names": {d["course_name"] for d in details},
        "details": details,
    }


def _reject_all(codes, name, comp):
    return SimilarMatch(False, 0.0, None)


def _group(candidates, required=1, target_min=3.0):
    return {
        "candidate_codes": set(candidates),
        "required_count": required,
        "target_min": target_min,
    }


# ── 진입요건: 듣는 중은 세지 않는다 ─────────────────────────────────
# 성적 기준 비교가 판정의 핵심이라 '아직 성적이 없는 과목'을 충족으로 칠 수 없다.

def test_entry_requirement_ignores_in_progress_for_qualifying():
    completed = _completed([_detail("CSE1017", "프로그래밍기초", None, in_progress=True)])
    b = scoring.entry_requirement_breakdown([_group(["CSE1017"])], completed)
    assert b["qualifying"] == 0


def test_in_progress_candidate_stays_pending_not_blocked():
    """듣는 중을 0점으로 세면 '성적 미달(blocked)'로 오판된다 — 아직 진행 전이다."""
    completed = _completed([_detail("CSE1017", "프로그래밍기초", None, in_progress=True)])
    b = scoring.entry_requirement_breakdown([_group(["CSE1017"])], completed)
    assert b["attempted"] == 0
    assert scoring.entry_gate_state(b) == scoring.GATE_PENDING


def test_entry_requirement_still_counts_graded_course():
    completed = _completed([_detail("CSE1017", "프로그래밍기초", 4.0)])
    b = scoring.entry_requirement_breakdown([_group(["CSE1017"])], completed)
    assert b["qualifying"] == 1
    assert scoring.entry_gate_state(b) == scoring.GATE_OPEN


def test_graded_below_threshold_is_still_blocked():
    """듣는 중 처리를 넣어도 '들었는데 성적 미달'은 그대로 blocked여야 한다."""
    completed = _completed([_detail("CSE1017", "프로그래밍기초", 1.0)])
    b = scoring.entry_requirement_breakdown([_group(["CSE1017"])], completed)
    assert b["attempted"] == 1
    assert scoring.entry_gate_state(b) == scoring.GATE_BLOCKED


def test_entry_requirement_reports_in_progress_count():
    """화면에 '수강중 N과목'을 띄우려면 개수가 분해 결과에 있어야 한다."""
    completed = _completed([
        _detail("CSE1017", "프로그래밍기초", None, in_progress=True),
        _detail("CSE1020", "창의융합설계", 4.0),
    ])
    b = scoring.entry_requirement_breakdown([_group(["CSE1017", "CSE1020"], required=2)], completed)
    assert b["qualifying"] == 1
    assert b["in_progress"] == 1


# ── 이수율: 듣는 중을 센다 ──────────────────────────────────────────
# "이 과목을 이수했는가"를 묻는 항목이라 성격이 다르다. 학생이 실제로 듣고 있다.

def test_curriculum_counts_in_progress_as_completed():
    completed = _completed([_detail("CUL7124", "AI리터러시", None, in_progress=True)])
    first_year = [{"course_code": "CUL7124", "course_name": "AI리터러시"}]
    exact, similar = scoring.curriculum_completion_score(first_year, completed, _reject_all)
    assert exact == 100.0


def test_recommended_counts_in_progress_as_completed():
    completed = _completed([_detail("CUL7124", "AI리터러시", None, in_progress=True)])
    exact, _ = scoring.recommended_courses_score(
        ["AI리터러시"], completed, {"AI리터러시": {"CUL7124"}}, _reject_all
    )
    assert exact == 100.0


# ── 화면 표시: 이수와 수강중을 갈라서 내려보낸다 ─────────────────────
# "8과목 이수 + 4과목 수강중 / 15과목"을 그리려면 합계만으로는 부족하다.

from unittest.mock import MagicMock  # noqa: E402

from lions_core.evaluation_presenter import EvaluationResponseBuilder  # noqa: E402


def _analysis_json(completed, first_year, entry_breakdown=None):
    def _no_similar(codes, name, comp):
        return SimilarMatch(False, 0.0, None)

    return EvaluationResponseBuilder.build_analysis_json(
        student=MagicMock(),
        department=MagicMock(),
        enrollments=[],
        student_completed_courses=completed,
        entry_breakdown=entry_breakdown or {
            "score": 100.0, "required": 0, "qualifying": 0, "attempted": 0,
            "in_progress": 0, "satisfied": True, "has_requirement": False,
        },
        recommended_exact_rate=0.0,
        recommended_similar_rate=0.0,
        curriculum_exact_rate=0.0,
        curriculum_similar_rate=0.0,
        necessary_courses=[],
        recommended_course_names=[],
        first_year_courses=first_year,
        course_name_to_codes={},
        is_graph_available=False,
        find_best_similar_course_func=_no_similar,
    )


def test_curriculum_reports_in_progress_separately():
    completed = _completed([
        _detail("A", "에이", 4.0),
        _detail("B", "비", None, in_progress=True),
    ])
    first_year = [
        {"course_code": "A", "course_name": "에이"},
        {"course_code": "B", "course_name": "비"},
        {"course_code": "C", "course_name": "씨"},
    ]
    cc = _analysis_json(completed, first_year)["curriculum_completion"]
    assert cc["exact_completed"] == 2          # 이수 1 + 수강중 1
    assert cc["in_progress_completed"] == 1    # 그중 수강중이 1


def test_entry_requirement_exposes_in_progress_count():
    breakdown = {
        "score": 0.0, "required": 2, "qualifying": 0, "attempted": 0,
        "in_progress": 1, "satisfied": False, "has_requirement": True,
    }
    er = _analysis_json(_completed([]), [], breakdown)["entry_requirement"]
    assert er["in_progress_courses"] == 1
    assert er["gate"] == scoring.GATE_PENDING
