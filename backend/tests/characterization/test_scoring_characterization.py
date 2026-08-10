"""
특성화 테스트 (Characterization) — lions-core 리팩토링 안전망 (Phase 0).

리팩토링 중 "절대 깨지면 안 되는 현재 동작"을 고정한다.
- _find_best_similar_course: 유사과목 판정 3단계 우선순위 (P4 도메인 추출 대상)
- analysis_json overall.weights/score: API 응답에 노출되는 가중치 계약 (P1/P2 대상)

주의: 가중치 값(0.4/0.3/0.3)은 "현재 동작"이며, 이 값이 원래 의도인지의 결정은
Phase 7(별도 트랙)에서 다룬다. 여기서는 리팩토링이 값을 바꾸지 않음만 보장한다.
"""

from unittest.mock import MagicMock

from services.evaluation_service import EvaluationService
from services.evaluation_presenter import EvaluationResponseBuilder


def _svc() -> EvaluationService:
    return EvaluationService(db=MagicMock())


def _completed(details):
    return {
        "codes": {d["course_code"] for d in details},
        "names": {d["course_name"] for d in details},
        "details": details,
    }


# ---------------------------------------------------------------------------
# _find_best_similar_course — 3단계 우선순위
# ---------------------------------------------------------------------------

def test_tier1_exact_code_wins_even_with_different_name():
    """1단계: 동일 학수코드는 이름이 달라도 항상 최우선, 유사도 1.0."""
    svc = _svc()
    svc._is_graph_available = MagicMock(return_value=False)
    completed = _completed([
        {"course_code": "CSE101", "course_name": "개론", "grade": "A+", "credits": 3}
    ])
    ok, sim, match = svc._find_best_similar_course({"CSE101"}, "완전다른이름", completed)
    assert ok is True
    assert sim == 1.0
    assert match["course_code"] == "CSE101"


def test_tier2_name_match_regardless_of_graph_connectivity():
    """2단계: 과목명 직접 일치는 Neo4j 연결 여부와 무관하게 인정, 유사도 1.0."""
    svc = _svc()
    svc._is_graph_available = MagicMock(return_value=False)
    completed = _completed([
        {"course_code": "OTHER999", "course_name": "자료구조", "grade": "B", "credits": 3}
    ])
    ok, sim, match = svc._find_best_similar_course({"CSE_UNSEEN"}, "자료구조", completed)
    assert ok is True
    assert sim == 1.0
    assert match["course_name"] == "자료구조"


def test_tier3_graph_similarity_at_or_above_threshold_accepted():
    """3단계: Neo4j 유사도 >= threshold(0.7)이면 인정."""
    svc = _svc()
    svc._is_graph_available = MagicMock(return_value=True)
    svc._get_similarity_from_graph = MagicMock(return_value=0.8)
    completed = _completed([
        {"course_code": "AAA", "course_name": "타과목", "grade": "A", "credits": 3}
    ])
    ok, sim, match = svc._find_best_similar_course({"BBB"}, "목표과목", completed)
    assert ok is True
    assert sim == 0.8
    assert match["course_code"] == "AAA"


def test_tier3_graph_similarity_below_threshold_rejected():
    """3단계: threshold 미만이면 미인정하되 최고유사도는 그대로 반환."""
    svc = _svc()
    svc._is_graph_available = MagicMock(return_value=True)
    svc._get_similarity_from_graph = MagicMock(return_value=0.5)
    completed = _completed([
        {"course_code": "AAA", "course_name": "타과목", "grade": "A", "credits": 3}
    ])
    ok, sim, match = svc._find_best_similar_course({"BBB"}, "목표과목", completed)
    assert ok is False
    assert sim == 0.5
    assert match is None


def test_graph_unavailable_and_no_direct_match_returns_zero():
    """그래프 미연결 + 코드/이름 불일치 → (False, 0.0, None)."""
    svc = _svc()
    svc._is_graph_available = MagicMock(return_value=False)
    completed = _completed([
        {"course_code": "AAA", "course_name": "타과목", "grade": "A", "credits": 3}
    ])
    ok, sim, match = svc._find_best_similar_course({"BBB"}, "목표과목", completed)
    assert ok is False
    assert sim == 0.0
    assert match is None


# ---------------------------------------------------------------------------
# analysis_json — 가중치·형태 계약 (P1 순환차단/P2 SSOT가 보존해야 함)
# ---------------------------------------------------------------------------

def test_analysis_json_overall_weights_and_score_contract():
    """overall.weights(0.4/0.3/0.3)와 score 산식, 최상위 키 집합을 고정한다."""
    completed = {"codes": set(), "names": set(), "details": []}

    def _no_similar(codes, name, comp):
        return (False, 0.0, None)

    aj = EvaluationResponseBuilder.build_analysis_json(
        student=MagicMock(),
        department=MagicMock(),
        enrollments=[],
        student_completed_courses=completed,
        entry_requirement_score=100.0,
        recommended_exact_rate=0.0,
        recommended_similar_rate=50.0,
        curriculum_exact_rate=0.0,
        curriculum_similar_rate=50.0,
        necessary_courses=[],
        recommended_course_names=[],
        first_year_courses=[],
        course_name_to_codes={},
        is_graph_available=False,
        find_best_similar_course_func=_no_similar,
    )

    assert set(aj.keys()) == {
        "entry_requirement",
        "recommended_courses",
        "curriculum_completion",
        "overall",
    }
    assert aj["overall"]["weights"] == {
        "entry_requirement": 0.4,
        "recommended_courses": 0.3,
        "curriculum_completion": 0.3,
    }
    # 100*0.4 + 50*0.3 + 50*0.3 = 70.0
    assert aj["overall"]["score"] == 70.0
