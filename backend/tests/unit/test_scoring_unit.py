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


# ---------------------------------------------------------------------------
# entry_requirement_breakdown — 표시(required/qualifying)와 점수 일관
# ---------------------------------------------------------------------------

def test_breakdown_no_groups():
    b = scoring.entry_requirement_breakdown([], _completed([]))
    # attempted: '아직 안 들음'과 '들었는데 성적 미달'을 가르기 위해 추가된 키.
    # in_progress: 지금 듣고 있는 후보 과목 수 — 점수에는 안 들어가고 표시에만 쓴다.
    assert b == {"score": 100.0, "required": 0, "qualifying": 0, "attempted": 0,
                 "in_progress": 0, "satisfied": True, "has_requirement": False}


def test_breakdown_reports_best_group_required_and_qualifying():
    groups = [
        {"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"C1"}},        # 0/1 -> 0%
        {"group": 2, "target_min": 3.0, "required_count": 2, "candidate_codes": {"C1", "C2"}},  # 1/2 -> 50%
    ]
    completed = _completed([_course_detail("C1", "x", 3.0)])
    b = scoring.entry_requirement_breakdown(groups, completed)
    assert b["score"] == 50.0          # best group progress
    assert b["required"] == 2          # best group's required_count
    assert b["qualifying"] == 1        # qualifying in the best group
    assert b["satisfied"] is False
    assert b["has_requirement"] is True


def test_breakdown_qualifying_clamped_to_required_when_satisfied():
    groups = [{"group": 1, "target_min": 3.0, "required_count": 2, "candidate_codes": {"B1", "B2", "B3"}}]
    completed = _completed([_course_detail(c, "x", 3.0) for c in ("B1", "B2", "B3")])  # 3 qualify, need 2
    b = scoring.entry_requirement_breakdown(groups, completed)
    assert b["score"] == 100.0
    assert b["required"] == 2
    assert b["qualifying"] == 2        # clamped (not 3) so display "2 / 2" matches 100%
    assert b["satisfied"] is True


def test_score_by_rules_delegates_to_breakdown():
    groups = [{"group": 1, "target_min": 3.0, "required_count": 2, "candidate_codes": {"B1", "B2"}}]
    completed = _completed([_course_detail("B1", "x", 3.0)])
    assert (
        scoring.entry_requirement_score_by_rules(groups, completed)
        == scoring.entry_requirement_breakdown(groups, completed)["score"]
        == 50.0
    )


# ---------------------------------------------------------------------------
# weighted_overall_score — 데이터 없는 항목은 가중치에서 제외(재정규화)
#
# 회귀 배경: 요건·권장 데이터가 없는 학과는 두 항목이 공허참 100%로 채워져
# 0.4*100 + 0.3*100 = 70점이 바닥으로 깔렸다(예: 데이터인텔리전스전공 74%).
# ---------------------------------------------------------------------------

WEIGHTS = {
    "entry_requirement": 0.4,
    "recommended_courses": 0.3,
    "curriculum_completion": 0.3,
}


def test_overall_all_present_matches_plain_weighted_sum():
    """세 항목 모두 존재하면 기존 가중합과 동일해야 한다(동작 보존)."""
    score = scoring.weighted_overall_score(
        {
            "entry_requirement": (80.0, True),
            "recommended_courses": (60.0, True),
            "curriculum_completion": (40.0, True),
        },
        WEIGHTS,
    )
    assert score == round(80.0 * 0.4 + 60.0 * 0.3 + 40.0 * 0.3, 2)


def test_overall_excludes_absent_components():
    """요건·권장 데이터가 없으면 교육과정 점수만 남아 그대로 종합 점수가 된다."""
    score = scoring.weighted_overall_score(
        {
            "entry_requirement": (100.0, False),
            "recommended_courses": (100.0, False),
            "curriculum_completion": (13.33, True),
        },
        WEIGHTS,
    )
    assert score == 13.33


def test_overall_renormalizes_remaining_weights():
    """한 항목만 빠지면 남은 두 항목의 가중치 합(0.6)으로 재정규화된다."""
    score = scoring.weighted_overall_score(
        {
            "entry_requirement": (100.0, False),
            "recommended_courses": (50.0, True),
            "curriculum_completion": (100.0, True),
        },
        WEIGHTS,
    )
    assert score == round((50.0 * 0.3 + 100.0 * 0.3) / 0.6, 2)


def test_overall_all_absent_is_zero():
    """평가할 근거가 하나도 없으면 0점(만점이 아니라)."""
    score = scoring.weighted_overall_score(
        {
            "entry_requirement": (100.0, False),
            "recommended_courses": (100.0, False),
            "curriculum_completion": (100.0, False),
        },
        WEIGHTS,
    )
    assert score == 0.0


def test_overall_regression_missing_requirement_data_no_longer_floors_at_70():
    """회귀: 데이터인텔리전스전공(요건·권장 미등록, 1학년 15과목 중 2과목 이수).

    과거 화면값 74% = 0.4*100(공허참) + 0.3*100(공허참) + 0.3*13.33.
    이제 근거 있는 교육과정 항목만 남아 13.33%가 그대로 종합 점수가 된다.
    """
    entry_breakdown = scoring.entry_requirement_breakdown([], _completed([]))
    curriculum_rate = round((2 / 15) * 100, 2)

    components = scoring.build_overall_components(
        entry_breakdown=entry_breakdown,
        recommended_similar_rate=100.0,
        recommended_total=0,
        curriculum_similar_rate=curriculum_rate,
        curriculum_total=15,
    )
    score = scoring.weighted_overall_score(components, WEIGHTS)

    assert score != 74.0
    assert score == curriculum_rate == 13.33


# ---------------------------------------------------------------------------
# is_evaluable — 평가 근거가 하나도 없으면 '0점'이 아니라 '평가 불가'
#
# 근거가 0개인 학과는 모든 학생에게 같은 값이 나온다(과거 100.0, 지금 0.0).
# 어느 쪽이든 학생을 구분하지 못하므로 점수로 제시하면 안 된다.
# ---------------------------------------------------------------------------

def test_evaluable_true_when_any_component_present():
    components = {
        "entry_requirement": (100.0, False),
        "recommended_courses": (100.0, False),
        "curriculum_completion": (13.33, True),
    }
    assert scoring.is_evaluable(components) is True


def test_evaluable_false_when_no_component_present():
    components = {
        "entry_requirement": (100.0, False),
        "recommended_courses": (100.0, False),
        "curriculum_completion": (100.0, False),
    }
    assert scoring.is_evaluable(components) is False
