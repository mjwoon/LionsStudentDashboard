"""
리포지토리 seam 기반 라우터 테스트.

기존 test_evaluation_router.py 는 db.query().filter().first() 체이닝을 수동
모킹해야 했다(구현 결합·취약). 리포지토리 도입 후에는 라우터가 의존하는
리포지토리만 대역으로 바꾸면 되어 테스트가 단순하고 견고해진다.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from database import get_db

client = TestClient(app)


def _override_noop_db():
    def _gen():
        yield MagicMock()

    app.dependency_overrides[get_db] = _gen


def test_not_found_via_repository_seam():
    """StudentRepository.get 이 None만 돌려주면 404 — 쿼리 체이닝 모킹 불필요."""
    _override_noop_db()
    try:
        with patch("routers.evaluation.StudentRepository") as SR:
            SR.return_value.get.return_value = None
            resp = client.get("/api/evaluation/student/123/department/9")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_cached_branch_via_repository_seam():
    """학생/캐시 리포지토리 대역만으로 캐시 분기 응답을 검증한다."""
    _override_noop_db()
    try:
        with patch("routers.evaluation.StudentRepository") as SR, patch(
            "routers.evaluation.EvaluationCacheRepository"
        ) as CR, patch("routers.evaluation.EvaluationService") as ES:
            student = MagicMock()
            student.student_id = 20250001
            SR.return_value.get.return_value = student

            cached = MagicMock()
            cached.overall_score = 85.0
            cached.is_satisfied = True
            cached.analysis_json = {}
            cached.calculated_at = None
            CR.return_value.get.return_value = cached

            ES.return_value.get_curriculum_details.return_value = {}

            resp = client.get("/api/evaluation/student/20250001/department/9")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is True
    assert data["grade"] == "B"  # 85.0 → B
