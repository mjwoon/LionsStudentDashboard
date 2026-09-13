"""운영 환경에 합성(생성) 요건 데이터가 들어가는 것을 막는다 (실제 SQLite).

배경: scripts/generate_dummy_requirements.py가 만든 합성 요건이 원본과 같은
CSV(group5_requirements_recs.csv)에 제자리 병합된다. 파일 하나뿐이라 관리자가 운영
업로드 화면에서 그 파일을 고르기 쉽고, 올라간 뒤에는 화면상 구분이 없다.
학생 입장에서는 존재하지 않는 요건을 '충족'으로 보고 진로를 정하게 되므로,
경계(업로드)에서 막고 이미 들어간 것은 기동 시 탐지한다.

판별은 `.generated-requirements.json` 대장(학과코드 × 행 종류)으로 한다.
requirement_text로 판별할 수 없는 이유는 test_generated_text_collides_with_real_regulation 참고.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from lions_core.generated_data import GeneratedDataManifest, load_manifest
from main import app
from models.models import Base, College, Department

client = TestClient(app)

HEADER = (
    "dept_code,admission_year,requirement_group,target_grade_level,required_count,"
    "requirement_text,is_alert_required,logic_operator,course_code,recommended_course\n"
)
# 실제 학사 규정 — 대장에 없는 학과(ELEC)
REAL_ROW = "ELEC,2026,1,A,1,아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수,True,AND,ELE3037,\n"
# 생성분 — 대장에 있는 학과(ACTU). 텍스트는 위 실제 규정과 글자 단위로 같다.
GENERATED_ROW = "ACTU,2026,1,A,1,아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수,True,AND,ACT2001,\n"
GENERATED_REC_ROW = "ACTU,,,,,,,,,보험수학\n"

MANIFEST = GeneratedDataManifest(["ACTU"], ["ACTU"])


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
    session.add(Department(id=300, code="ELEC", name="전자공학부", college_id=3))
    session.add(Department(id=301, code="ACTU", name="보험계리학과", college_id=3))
    session.commit()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()


@pytest.fixture
def manifest(monkeypatch):
    """업로드 가드가 보는 대장을 테스트용으로 고정한다."""
    monkeypatch.setattr(
        "routers.admin_upload_grouped.load_manifest", lambda *a, **k: MANIFEST
    )


def _upload(csv_text):
    return client.post(
        "/api/admin/upload-grouped/requirements",
        files={"file": ("req.csv", io.BytesIO(csv_text.encode("utf-8-sig")), "text/csv")},
    )


# ---------------------------------------------------------------------------
# 왜 텍스트로 판별하지 않는가
# ---------------------------------------------------------------------------

def test_generated_text_collides_with_real_regulation():
    """생성기의 requirement_text는 실제 ELEC 규정과 글자 단위로 같다.

    #12의 '[더미]' 접두어가 사라진 뒤 문자열 판별로 되돌리려는 시도를 막는 회귀
    테스트다. 아래가 참인 한, requirement_text를 보는 판별식은 진짜 학사 규정을
    오탐한다.
    """
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "gen", root / "scripts" / "generate_dummy_requirements.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    candidates = [{"학수번호": f"X{i}", "교과목이름": f"과목{i}"} for i in range(5)]
    generated_text = gen.requirement_rows("ACTU", candidates)[0]["requirement_text"]

    assert generated_text in REAL_ROW, (
        "생성 텍스트가 실제 ELEC 규정과 더는 같지 않다. 그래도 문자열 판별로 "
        "되돌리기 전에 모든 실제 규정과 대조하라."
    )


# ---------------------------------------------------------------------------
# 경계 방어 — 운영에서는 생성분이 섞인 CSV를 받지 않는다
# ---------------------------------------------------------------------------

def test_production_rejects_csv_containing_generated_rows(db, manifest, monkeypatch):
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "production")

    resp = _upload(HEADER + REAL_ROW + GENERATED_ROW)

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "합성" in detail
    # 몇 행이 문제인지 알려줘야 조치할 수 있다. 생성분은 3행(헤더+실제행 다음).
    assert "3행" in detail or ": 3" in detail


def test_production_rejects_generated_recommendation_rows(db, manifest, monkeypatch):
    """권장과목 전용 행(요건그룹이 빈 행)도 잡는다."""
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "production")

    assert _upload(HEADER + GENERATED_REC_ROW).status_code == 400


def test_production_accepts_real_regulation_with_identical_text(db, manifest, monkeypatch):
    """실제 규정은 생성분과 텍스트가 같아도 통과해야 한다 — 오탐 방지의 핵심."""
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "production")

    assert _upload(HEADER + REAL_ROW).status_code == 200


def test_development_still_accepts_generated_rows(db, manifest, monkeypatch):
    """개발·실험 환경은 합성 데이터가 목적이므로 그대로 받는다."""
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "development")

    assert _upload(HEADER + REAL_ROW + GENERATED_ROW).status_code == 200


def test_empty_manifest_does_not_block_uploads(db, monkeypatch):
    """대장이 없으면 막을 근거가 없다 — 전부 차단하지는 않되 로그로 드러낸다."""
    monkeypatch.setattr("routers.admin_upload_grouped.settings.app_env", "production")
    monkeypatch.setattr(
        "routers.admin_upload_grouped.load_manifest",
        lambda *a, **k: GeneratedDataManifest([], []),
    )

    assert _upload(HEADER + GENERATED_ROW).status_code == 200


# ---------------------------------------------------------------------------
# 사후 탐지 — 이미 들어간 생성분을 기동 시 찾아낸다
# ---------------------------------------------------------------------------

def test_startup_check_counts_existing_generated_rows(db, monkeypatch):
    from db_migrations import count_generated_requirements
    from models.models import CourseRecommendation, DepartmentEntryRequirement

    monkeypatch.setattr("db_migrations.load_manifest", lambda *a, **k: MANIFEST)

    db.add(DepartmentEntryRequirement(  # 생성분 (ACTU)
        department_id=301, admission_year=2026, requirement_group=1,
        target_grade_level="A", required_count=1,
        requirement_text="아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수",
    ))
    db.add(DepartmentEntryRequirement(  # 실제 규정 (ELEC) — 텍스트가 같아도 세지 않는다
        department_id=300, admission_year=2026, requirement_group=1,
        target_grade_level="A", required_count=1,
        requirement_text="아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수",
    ))
    db.add(CourseRecommendation(department_id=301, course_name="보험수학"))
    db.commit()

    assert count_generated_requirements(db) == (1, 1)


def test_startup_check_returns_zero_on_clean_db(db, monkeypatch):
    from db_migrations import count_generated_requirements

    monkeypatch.setattr("db_migrations.load_manifest", lambda *a, **k: MANIFEST)

    assert count_generated_requirements(db) == (0, 0)


# ---------------------------------------------------------------------------
# 대장과 실제 데이터가 어긋나지 않는지
# ---------------------------------------------------------------------------

def test_repo_manifest_does_not_overlap_real_regulations():
    """대장의 학과와 실제 규정 보유 학과는 겹치지 않아야 한다.

    겹치면 가드가 진짜 학사 규정을 막는다. 학교가 새 규정을 주면 대장에서 그
    학과코드를 빼야 하며, 이 테스트가 그것을 잊지 않게 한다.
    """
    import csv
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    manifest = load_manifest(root / ".generated-requirements.json")
    with open(root / "group5_requirements_recs.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    real_req = {
        r["dept_code"] for r in rows
        if r["requirement_group"] and r["dept_code"] not in manifest.requirement_dept_codes
    }
    real_rec = {
        r["dept_code"] for r in rows
        if r["recommended_course"] and r["dept_code"] not in manifest.recommendation_dept_codes
    }

    assert not (real_req & manifest.requirement_dept_codes)
    assert not (real_rec & manifest.recommendation_dept_codes)
