"""운영 환경에 합성(더미) 요건 데이터가 들어가는 것을 막는다 (실제 SQLite).

배경: scripts/generate_dummy_requirements.py가 만든 합성 요건이 원본과 같은
CSV(group5_requirements_recs.csv)에 병합돼 있다. 파일 하나뿐이라 관리자가 운영
업로드 화면에서 그 파일을 고르기 쉽고, 올라간 뒤에는 구분할 방법이 없다 —
'[더미]' 접두어가 붙는 requirement_text는 API 응답에도 화면에도 실리지 않는다.

학생 입장에서는 존재하지 않는 요건을 '충족'으로 보고 진로를 정하게 되므로,
경계(업로드)에서 막고 이미 들어간 것은 기동 시 탐지한다.
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
REAL_ROW = "CS_CS,2026,1,A,1,아래 2개 과목 중 B 이상 1과목 필수,True,AND,CSE1017,\n"
DUMMY_ROW = "CS_CS,2026,2,B,2,[더미] 아래 5개 과목 중 성적 B 이상 2과목 필수,True,AND,CSE1017,\n"


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


# ---------------------------------------------------------------------------
# 경계 방어 — 운영에서는 더미가 섞인 CSV를 받지 않는다
# ---------------------------------------------------------------------------

def test_production_rejects_csv_containing_dummy_rows(db, monkeypatch):
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "production")

    resp = _upload(HEADER + REAL_ROW + DUMMY_ROW)

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "더미" in detail
    # 몇 행이 문제인지 알려줘야 조치할 수 있다.
    assert "1" in detail


def test_production_accepts_csv_without_dummy_rows(db, monkeypatch):
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "production")

    assert _upload(HEADER + REAL_ROW).status_code == 200


def test_development_still_accepts_dummy_rows(db, monkeypatch):
    """개발·실험 환경은 더미가 목적이므로 그대로 받는다."""
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "development")

    assert _upload(HEADER + REAL_ROW + DUMMY_ROW).status_code == 200


# ---------------------------------------------------------------------------
# 사후 탐지 — 이미 들어간 더미를 기동 시 찾아낸다
# ---------------------------------------------------------------------------

def test_startup_check_counts_existing_dummy_requirements(db):
    from models.models import DepartmentEntryRequirement
    from db_migrations import count_dummy_requirements

    db.add(DepartmentEntryRequirement(
        department_id=300, admission_year=2026, requirement_group=1,
        target_grade_level="A", required_count=1,
        requirement_text="[더미] 아래 5개 과목 중 성적 B 이상 2과목 필수",
    ))
    db.add(DepartmentEntryRequirement(
        department_id=300, admission_year=2026, requirement_group=2,
        target_grade_level="B", required_count=1,
        requirement_text="아래 2개 과목 중 B 이상 1과목 필수",
    ))
    db.commit()

    assert count_dummy_requirements(db) == 1


def test_startup_check_returns_zero_on_clean_db(db):
    from db_migrations import count_dummy_requirements

    assert count_dummy_requirements(db) == 0
