"""대시보드 통계 응답의 키 계약 (실제 SQLite).

이 엔드포인트는 테스트가 전혀 없었고, 같은 경로를 두 라우터가 선언하고 있었다.
surveys.py(/api + /dashboard/stats)가 main.py에서 먼저 등록되므로 그쪽이 응답하고
routers/dashboard.py의 동명 핸들러는 한 번도 실행되지 않았다 - 기동할 때마다
"Duplicate Operation ID get_dashboard_stats" 경고가 그 사실을 알리고 있었다.

도달하지 못한 쪽이 계산하던 student_stats / grade_distribution / department_gpa_stats는
Student.current_gpa·total_credits 컬럼을 읽는데, 그 컬럼에 값을 쓰는 코드가 저장소에
없었다(update_student_gpa는 호출자가 없어 제거됨). 실행됐더라도 전부 0이었을 값이고,
프론트엔드 DashboardStatsResponse에 필드 자체가 없어 소비되지도 않는다.

여기서는 실제로 응답하는 쪽의 키를 고정한다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models.models import Base, College, Department, SurveyRound

client = TestClient(app)

# 프론트엔드 DashboardStatsResponse가 읽는 키
CONSUMED_KEYS = {
    "colleges",
    "departments",
    "current_data",
    "trend_data",
    "survey_info",
    "survey_rounds",
    "current_data_by_round",
}

# 도달 불가였던 중복 핸들러가 계산하던 키들 — 다시 들어오면 안 된다
REMOVED_KEYS = {"student_stats", "grade_distribution", "department_gpa_stats"}


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(College(id=2, name="공학대학"))
    session.add(Department(id=200, code="ELEC", name="전자공학부", college_id=2))
    # 설문 회차가 없으면 엔드포인트가 빈 목록으로 조기 반환한다 — 전체 경로를 태운다.
    session.add(SurveyRound(id=1, round_number=1, title="1차 희망전공 조사", status="OPEN"))
    session.commit()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_stats_returns_keys_the_frontend_reads(db):
    body = client.get("/api/dashboard/stats").json()

    assert CONSUMED_KEYS <= set(body), f"빠진 키: {CONSUMED_KEYS - set(body)}"


def test_stats_does_not_return_dead_gpa_keys(db):
    """되살리려면 먼저 Student.current_gpa·total_credits를 채우는 코드가 있어야 한다."""
    body = client.get("/api/dashboard/stats").json()

    assert not (REMOVED_KEYS & set(body))


def test_stats_returns_registered_departments(db):
    body = client.get("/api/dashboard/stats").json()

    assert [d["name"] for d in body["colleges"]] == ["공학대학"]
    assert any(d["name"] == "전자공학부" for d in body["departments"])


def test_stats_returns_empty_lists_without_a_survey_round(db):
    """설문 회차가 없으면 학과·집계는 빈 목록이다 — 조기 반환 경로."""
    db.query(SurveyRound).delete()
    db.commit()

    body = client.get("/api/dashboard/stats").json()

    assert body["departments"] == []
    assert body["current_data"] == []
    assert [c["name"] for c in body["colleges"]] == ["공학대학"]
