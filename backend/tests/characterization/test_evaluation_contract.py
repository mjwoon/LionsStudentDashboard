"""
특성화 테스트 (Characterization tests) — 리팩토링 안전망.

이 테스트들은 "바꿔야 할 것"이 아니라 "리팩토링 중 절대 깨지면 안 되는
현재의 관찰 가능한 동작"을 고정한다. P1(설정/인프라 분리, lifespan 전환)과
P5(폐기 API 정리, 스키마 분할)는 모두 행위 보존이 원칙이므로, 아래 계약이
초록색으로 유지되는 한 그 변경들은 안전하다.

주의: 입학연도(admission_year) 동작은 "의도적으로 변경"할 대상이므로 여기서
고정하지 않는다. 해당 동작은 별도 테스트(test_admission_year.py)에서 다룬다.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.models import Student, StudentRequirementStatus

client = TestClient(app)


def _make_cache_branch_db(student_id: int, cached):
    """db.query(...)가 모델에 따라 학생/캐시 레코드를 돌려주도록 구성."""
    mock_db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model is Student:
            student = MagicMock()
            student.student_id = student_id
            q.filter.return_value.first.return_value = student
        elif model is StudentRequirementStatus:
            q.filter.return_value.first.return_value = cached
        else:
            q.filter.return_value.first.return_value = None
        return q

    mock_db.query.side_effect = query_side_effect
    return mock_db


def _override_db(mock_db):
    def _gen():
        yield mock_db

    app.dependency_overrides[get_db] = _gen


# ---------------------------------------------------------------------------
# 1. 캐시 분기 응답 계약 (직렬화 형태가 바뀌면 프론트가 깨진다)
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "student_id",
    "department_id",
    "entry_requirement_score",
    "recommended_exact_rate",
    "recommended_similar_rate",
    "curriculum_exact_rate",
    "curriculum_similar_rate",
    "overall_score",
    "grade",
    "summary_message",
    "evaluated_at",
    "cached",
    "analysis_json",
    "ai_summary",
    "curriculum_details",
}


def test_cached_evaluation_response_contract():
    """캐시된 평가 조회의 응답 키 집합과 핵심 값 형태를 고정한다."""
    student_id = 20260001

    cached = MagicMock()
    cached.overall_score = 95.5
    cached.is_satisfied = True
    cached.analysis_json = {
        "entry_requirement": {"score": 100.0},
        "recommended_courses": {"exact_rate": 80, "similar_rate": 20},
        "curriculum_completion": {"exact_rate": 90, "similar_rate": 10},
        "ai_summary": "우수합니다.",
    }
    cached.calculated_at = None

    mock_db = _make_cache_branch_db(student_id, cached)
    _override_db(mock_db)
    try:
        with patch("routers.evaluation.EvaluationService") as EvalSvc:
            EvalSvc.return_value.get_curriculum_details.return_value = {}
            resp = client.get(f"/api/evaluation/student/{student_id}/department/99")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == EXPECTED_KEYS
    assert data["cached"] is True
    assert data["overall_score"] == 95.5
    assert data["entry_requirement_score"] == 100.0
    assert data["summary_message"] == "진입요건 충족"
    assert data["ai_summary"] == "우수합니다."


# ---------------------------------------------------------------------------
# 2. 등급 임계값 로직 (P4에서 SSOT로 통합 예정 — 값이 바뀌면 안 됨)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "score, expected_grade",
    [
        (100.0, "A"),
        (90.0, "A"),
        (89.99, "B"),
        (80.0, "B"),
        (79.99, "C"),
        (70.0, "C"),
        (69.99, "D"),
        (60.0, "D"),
        (59.99, "F"),
        (0.0, "F"),
    ],
)
def test_grade_thresholds(score, expected_grade):
    """overall_score → 등급 경계값을 고정한다."""
    student_id = 20260002

    cached = MagicMock()
    cached.overall_score = score
    cached.is_satisfied = score >= 70
    cached.analysis_json = {}
    cached.calculated_at = None

    mock_db = _make_cache_branch_db(student_id, cached)
    _override_db(mock_db)
    try:
        with patch("routers.evaluation.EvaluationService") as EvalSvc:
            EvalSvc.return_value.get_curriculum_details.return_value = {}
            resp = client.get(f"/api/evaluation/student/{student_id}/department/99")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["grade"] == expected_grade


# ---------------------------------------------------------------------------
# 3. 학생 미존재 → 404 (예외 경로 보존)
# ---------------------------------------------------------------------------


def test_student_not_found_returns_404():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    _override_db(mock_db)
    try:
        resp = client.get("/api/evaluation/student/999/department/1")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert "찾을 수 없습니다" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 4. 라우터 등록 보존 (main.py의 lifespan 전환이 라우트를 떨어뜨리지 않게 가드)
# ---------------------------------------------------------------------------


def test_expected_routes_are_registered():
    # FastAPI 0.14x는 include_router 결과를 지연(_IncludedRouter)으로 담아
    # app.routes 순회로는 중첩 라우트가 보이지 않는다. 등록 여부는 버전 안정적인
    # OpenAPI 스키마의 paths로 검증한다(동작 검증 의도는 동일).
    paths = set(app.openapi()["paths"].keys())
    expected = {
        "/",
        "/health",
        "/api/evaluation/student/{student_id}/department/{department_id}",
        "/api/evaluation/student/{student_id}/all-departments",
        "/api/evaluation/batch/department/{department_id}",
    }
    missing = expected - paths
    assert not missing, f"등록되지 않은 라우트: {missing}"
