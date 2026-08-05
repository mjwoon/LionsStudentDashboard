"""
입학연도(admission_year) 도출 동작 검증.

이전에는 엔드포인트마다 고정 기본값(2026/2025)이 박혀 있어 같은 학생이라도
호출 경로에 따라 다른 연도로 평가되는 정합성 문제가 있었다. 이제는 미지정 시
학번에서 도출하고, 명시적으로 주어지면 그 값으로 override 한다.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.models import Student, StudentRequirementStatus

client = TestClient(app)


def _fresh_path_db(student_id: int):
    """학생은 존재하되 캐시는 없어(=신규 계산 경로) evaluate_student가 호출되도록."""
    mock_db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model is Student:
            student = MagicMock()
            student.student_id = student_id
            q.filter.return_value.first.return_value = student
        elif model is StudentRequirementStatus:
            q.filter.return_value.first.return_value = None  # 캐시 없음
        else:
            q.filter.return_value.first.return_value = None
        return q

    mock_db.query.side_effect = query_side_effect
    return mock_db


def _run(student_id: int, query: str = ""):
    mock_db = _fresh_path_db(student_id)

    def _gen():
        yield mock_db

    app.dependency_overrides[get_db] = _gen
    try:
        with patch("routers.evaluation.EvaluationService") as EvalSvc:
            instance = EvalSvc.return_value
            instance.evaluate_student.return_value = {"overall_score": 50.0}
            instance.get_curriculum_details.return_value = {}
            # get_admission_year_from_student_id 는 실제 로직을 그대로 사용
            EvalSvc.get_admission_year_from_student_id.side_effect = (
                lambda s: int(str(s)[:4])
            )
            resp = client.get(
                f"/api/evaluation/student/{student_id}/department/99{query}"
            )
            return resp, instance
    finally:
        app.dependency_overrides.clear()


def test_admission_year_derived_from_student_id_when_omitted():
    """미지정 시 학번 앞 4자리(2024)로 평가한다."""
    resp, instance = _run(20240001)
    assert resp.status_code == 200
    # evaluate_student(student_id, department_id, admission_year, save_to_db=...)
    _, _, passed_year = instance.evaluate_student.call_args.args[:3]
    assert passed_year == 2024


def test_admission_year_explicit_override_is_respected():
    """명시적으로 주면 그 값을 사용한다."""
    resp, instance = _run(20240001, query="?admission_year=2030")
    assert resp.status_code == 200
    _, _, passed_year = instance.evaluate_student.call_args.args[:3]
    assert passed_year == 2030
