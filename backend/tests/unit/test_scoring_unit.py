"""
lions_core.scoring 순수 함수 단위 테스트 (Phase 4c).

DB·Neo4j·SQLAlchemy 모킹이 전혀 없다. 평범한 dict과 lambda만으로 결정론적으로
검증된다 — 도메인 로직을 IO에서 분리한 결과(테스트 피라미드의 빠른 바닥).
"""

from lions_core import scoring
from lions_core.scoring import SimilarMatch


def _completed(details):
    return {
        "codes": {d["course_code"] for d in details},
        "names": {d["course_name"] for d in details},
        "details": details,
    }


def _course_detail(code, name, numeric):
    return {"course_code": code, "course_name": name, "grade": "", "credits": 3, "numeric_grade": numeric}


def _accept_all(codes, name, comp):
    return SimilarMatch(True, 1.0, None)


def _reject_all(codes, name, comp):
    return SimilarMatch(False, 0.0, None)


# ---------------------------------------------------------------------------
# recommended_courses_score
# ---------------------------------------------------------------------------

def test_recommended_empty_is_100_100():
    assert scoring.recommended_courses_score([], _completed([]), {}, _reject_all) == (100.0, 100.0)


def test_recommended_exact_requires_name_and_code():
    completed = _completed([{"course_code": "CSE201", "course_name": "이산수학", "grade": "A", "credits": 3}])
    name_to_codes = {"이산수학": {"CSE201"}}
    exact, similar = scoring.recommended_courses_score(["이산수학"], completed, name_to_codes, _reject_all)
    assert exact == 100.0   # 과목명 일치 + 코드 교집합
    assert similar == 0.0    # matcher가 거부


def test_recommended_similar_counts_via_matcher():
    completed = _completed([{"course_code": "X", "course_name": "y", "grade": "A", "credits": 3}])
    exact, similar = scoring.recommended_courses_score(["무엇"], completed, {}, _accept_all)
    assert exact == 0.0
    assert similar == 100.0


# ---------------------------------------------------------------------------
# curriculum_completion_score
# ---------------------------------------------------------------------------

def test_curriculum_empty_is_100_100():
    assert scoring.curriculum_completion_score([], _completed([]), _reject_all) == (100.0, 100.0)


def test_curriculum_exact_by_code_half():
    first_year = [
        {"course_code": "CSE101", "course_name": "개론"},
        {"course_code": "CSE102", "course_name": "기초"},
    ]
    completed = _completed([{"course_code": "CSE101", "course_name": "개론", "grade": "A", "credits": 3}])
    exact, similar = scoring.curriculum_completion_score(first_year, completed, _reject_all)
    assert exact == 50.0
    assert similar == 0.0


# ---------------------------------------------------------------------------
# find_best_similar_course — 3단계 + 지연 평가
# ---------------------------------------------------------------------------

def test_tier1_exact_code_does_not_touch_graph():
    """1단계 매칭 시 그래프 가용성 확인조차 호출되지 않아야 한다(지연 평가)."""
    calls = []

    def avail():
        calls.append(1)
        return True

    completed = _completed([{"course_code": "CSE101", "course_name": "개론", "grade": "A", "credits": 3}])
    m = scoring.find_best_similar_course(
        {"CSE101"}, "완전다른이름", completed,
        is_graph_available=avail, get_similarity=lambda a, b: 1.0, threshold=0.7,
    )
    assert m.accepted and m.similarity == 1.0
    assert calls == []  # 그래프 미접촉


def test_tier2_name_match_without_graph():
    completed = _completed([{"course_code": "OTHER", "course_name": "자료구조", "grade": "B", "credits": 3}])
    m = scoring.find_best_similar_course(
        {"UNSEEN"}, "자료구조", completed,
        is_graph_available=lambda: False, get_similarity=lambda a, b: 0.0, threshold=0.7,
    )
    assert m.accepted is True
    assert m.similarity == 1.0
    assert m.matched["course_name"] == "자료구조"


def test_tier3_at_or_above_threshold_accepted():
    completed = _completed([{"course_code": "AAA", "course_name": "타", "grade": "A", "credits": 3}])
    m = scoring.find_best_similar_course(
        {"BBB"}, "목표", completed,
        is_graph_available=lambda: True, get_similarity=lambda a, b: 0.8, threshold=0.7,
    )
    assert m.accepted is True
    assert m.similarity == 0.8
    assert m.matched["course_code"] == "AAA"


def test_tier3_below_threshold_rejected_keeps_best_similarity():
    completed = _completed([{"course_code": "AAA", "course_name": "타", "grade": "A", "credits": 3}])
    m = scoring.find_best_similar_course(
        {"BBB"}, "목표", completed,
        is_graph_available=lambda: True, get_similarity=lambda a, b: 0.5, threshold=0.7,
    )
    assert m == SimilarMatch(False, 0.5, None)


def test_graph_unavailable_returns_zero_even_if_similarity_would_be_high():
    completed = _completed([{"course_code": "AAA", "course_name": "타", "grade": "A", "credits": 3}])
    m = scoring.find_best_similar_course(
        {"BBB"}, "목표", completed,
        is_graph_available=lambda: False, get_similarity=lambda a, b: 0.9, threshold=0.7,
    )
    assert m == SimilarMatch(False, 0.0, None)


# ---------------------------------------------------------------------------
# entry_requirement_score_by_rules
# ---------------------------------------------------------------------------

def test_rules_no_groups_is_100():
    assert scoring.entry_requirement_score_by_rules([], _completed([])) == 100.0


def test_rules_group_satisfied_is_100():
    groups = [{"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"A1", "A2"}}]
    completed = _completed([_course_detail("A1", "x", 4.0)])
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 100.0


def test_rules_group_partial_progress():
    groups = [{"group": 1, "target_min": 3.0, "required_count": 2, "candidate_codes": {"B1", "B2", "B3"}}]
    completed = _completed([_course_detail("B1", "x", 3.0)])  # 1 of 2 qualifying
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 50.0


def test_rules_all_groups_or_takes_max():
    groups = [
        {"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"C1"}},        # need A: 0%
        {"group": 2, "target_min": 3.0, "required_count": 2, "candidate_codes": {"C1", "C2"}},  # have 1/2: 50%
    ]
    completed = _completed([_course_detail("C1", "x", 3.0)])
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 50.0


def test_rules_grade_below_target_excluded():
    groups = [{"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"D1"}}]
    completed = _completed([_course_detail("D1", "x", 3.3)])  # B+ < 4.0
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 0.0
