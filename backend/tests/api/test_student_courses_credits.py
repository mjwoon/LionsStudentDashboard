"""학생 수강 화면의 '총 취득학점'은 취득한 것만 센다 (실제 SQLite).

배경: 이 엔드포인트는 수강 이력을 조건 없이 전부 더하고 있었다.

    total_credits = sum(enrollment.credits for enrollment in enrollments)

라벨은 '총 취득학점'인데 집계는 '총 수강학점'이었다. 실제 운영 데이터에서
2026665579 학생이 취득 16학점 + 수강중 12학점 = 28학점으로 표시됐다. 수강중 과목은
성적이 없으니 아직 학점이 아니고, F는 이수가 아니다.

판정 기준은 lions_core.enrollment 한 곳에 있다 — 평가 점수·교육과정 표와 같은 기준이다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models.models import Base, College, Department, Student, StudentCourse

client = TestClient(app)

STUDENT_PK = 2026665579


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(College(id=1, name="라이언스칼리지"))
    session.add(Department(id=101, code="LIONS2", name="자연계열", college_id=1))
    session.add(Student(
        student_id=STUDENT_PK, name="김지호", email="a@b.c", phone="010",
        department_id=101, class_number=1, track="자연계열", status="재학",
    ))
    session.commit()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()


def _enroll(db, course_code, credits, grade, numeric_grade=None):
    db.add(StudentCourse(
        student_id=STUDENT_PK, course_code=course_code, course_name=course_code,
        credits=credits, grade=grade, numeric_grade=numeric_grade,
        completion_type="전공기초", year=2026, semester=2,
    ))


def _total_credits(db):
    db.commit()
    resp = client.get(f"/api/students/{STUDENT_PK}/courses")
    assert resp.status_code == 200
    return resp.json()["total_credits"]


def test_in_progress_courses_are_not_counted_as_earned(db):
    """성적이 아직 없는 수강은 학점이 아니다 — 이 화면이 틀렸던 지점."""
    _enroll(db, "GEN0063", 3, "A0", 4.0)   # 취득
    _enroll(db, "GEN2053", 3, None)        # 수강중
    _enroll(db, "ELE3037", 3, "")          # 수강중 (빈 문자열)

    assert _total_credits(db) == 3


def test_failed_courses_are_not_counted_as_earned(db):
    """F는 이수가 아니다."""
    _enroll(db, "GEN0063", 3, "A0", 4.0)
    _enroll(db, "GEN0064", 3, "F", 0.0)

    assert _total_credits(db) == 3


def test_earned_courses_are_counted(db):
    _enroll(db, "GEN0063", 3, "A0", 4.0)
    _enroll(db, "CUL2100", 2, "B+", 3.5)
    _enroll(db, "GEN0067", 1, "P")  # P(패스)도 이수다

    assert _total_credits(db) == 6


def test_total_matches_sum_of_earned_rows_in_the_table(db):
    """합계는 화면 표의 취득 행들과 맞아야 한다.

    운영 데이터의 2026665579 학생 구성 그대로: 취득 16 + 수강중 12.
    고치기 전에는 28이 나왔다.
    """
    for code, credits in [("A", 3), ("B", 3), ("C", 3), ("D", 2), ("E", 2), ("F1", 1), ("G", 1), ("H", 1)]:
        _enroll(db, code, credits, "B0", 3.0)          # 16학점
    for code, credits in [("CUL2100", 2), ("GEN2053", 3), ("ELE3037", 3), ("GEN0064", 3), ("GEN0067", 1)]:
        _enroll(db, code, credits, None)               # 12학점, 수강중

    db.commit()
    body = client.get(f"/api/students/{STUDENT_PK}/courses").json()
    assert body["total_credits"] == 16
    assert len(body["course_history"]) == 13  # 표에는 수강중도 그대로 보인다
