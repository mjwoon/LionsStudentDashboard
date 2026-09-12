"""요건 업로드에서 조용히 버려지던 행을 응답으로 드러낸다 (실제 SQLite).

회귀 배경: group5 CSV의 dept_code가 'CS'였는데 학과 마스터에는 'CS_CS'(컴퓨터학부)만
있었다. 요건과목 매핑 단계는 학과를 못 찾으면 아무 말 없이 `continue` 했고, 그 탓에
컴퓨터학부 요건이 통째로 빠진 채로 아무도 모르고 지나갔다.
업로드가 삼킨 행은 건수와 사유가 응답에 남아야 한다.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models.models import Base, College, Department

client = TestClient(app)

HEADER = (
    "dept_code,admission_year,requirement_group,target_grade_level,required_count,"
    "requirement_text,is_alert_required,logic_operator,course_code,recommended_course\n"
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(College(id=3, name="소프트웨어융합대학"))
    session.add(Department(id=300, code="CS_CS", name="컴퓨터학부", college_id=3))
    session.commit()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()


def _upload(csv_text):
    return client.post(
        "/api/admin/upload-grouped/requirements",
        files={"file": ("req.csv", io.BytesIO(csv_text.encode("utf-8-sig")), "text/csv")},
    )


def _skipped(resp):
    for sub in resp.json()["sub_results"]:
        if sub["label"] == "요건 과목 매핑":
            return sub
    raise AssertionError("요건 과목 매핑 결과가 없다")


def test_unknown_department_code_is_reported_not_swallowed(db):
    """학과 마스터에 없는 dept_code('CS')는 건수와 사유로 보고된다."""
    resp = _upload(HEADER + "CS,2026,1,A,1,요건,True,AND,CSE1017,\n")
    assert resp.status_code == 200

    sub = _skipped(resp)
    assert sub["skipped_count"] == 1
    reasons = " ".join(sub["skipped_reasons"])
    assert "CS" in reasons
    assert "학과" in reasons


def test_matching_department_code_is_not_reported_as_skipped(db):
    """정상 매칭되는 행은 건너뛴 것으로 잡히지 않는다."""
    resp = _upload(HEADER + "CS_CS,2026,1,A,1,요건,True,AND,CSE1017,\n")
    assert resp.status_code == 200
    assert _skipped(resp)["skipped_count"] == 0
