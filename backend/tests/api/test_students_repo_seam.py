"""
students 라우터의 not-found 경로 가드(리포지토리 seam).

이 라우터들은 그동안 테스트가 없었다. 리포지토리 도입을 계기로 최소한의
404 계약을 고정한다.
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


def test_student_courses_not_found():
    _override_noop_db()
    try:
        with patch("routers.students.StudentRepository") as SR:
            SR.return_value.get.return_value = None
            resp = client.get("/api/students/999/courses")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert "학생을 찾을 수 없습니다" in resp.json()["detail"]


def test_student_surveys_not_found():
    _override_noop_db()
    try:
        with patch("routers.students.StudentRepository") as SR:
            SR.return_value.get.return_value = None
            resp = client.get("/api/students/999/surveys")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
