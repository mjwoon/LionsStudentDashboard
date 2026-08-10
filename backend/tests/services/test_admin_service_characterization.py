"""
AdminService 특성화 테스트 (실제 in-memory SQLite 사용).

AdminService(841줄 God-object)에는 그동안 테스트가 없었다. P3 분해 전에
현재의 관찰 가능한 동작을 실제 DB로 고정한다 — 업로드 / 대량평가 오케스트레이션 /
캐시 관리 세 책임 각각.

대량평가 테스트는 EvaluationService.evaluate_student를 스텁으로 대체해
'오케스트레이션'(입학연도 계산, 캐시 분기, 카운트)만 검증한다. 클래스 메서드에
패치하므로 이후 코드가 다른 모듈로 이동해도 테스트는 그대로 유효하다.
"""

import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import (
    Base,
    College,
    Course,
    Department,
    Student,
    StudentRequirementStatus,
)
from models.schemas import CollegeDataUpload, CourseDataUpload, BulkEvaluationRequest
from services.admin_service import AdminService
from services.upload_service import UploadService
from services.evaluation_admin_service import EvaluationAdminService
import services.evaluation_service as eval_mod


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _seed_department(db, id, code, name):
    dept = Department(id=id, code=code, name=name)
    db.add(dept)
    db.commit()
    return dept


def _seed_student(db, student_id, department_id):
    st = Student(
        student_id=student_id,
        name="테스터",
        email=f"{student_id}@example.com",
        phone="010-0000-0000",
        department_id=department_id,
    )
    db.add(st)
    db.commit()
    return st


# ---------------------------------------------------------------------------
# 업로드 책임
# ---------------------------------------------------------------------------


def test_upload_colleges_insert_then_update(db):
    resp = UploadService.upload_colleges(
        db, [CollegeDataUpload(name="A"), CollegeDataUpload(name="B")]
    )
    assert resp.success
    assert resp.uploaded_count == 2
    assert resp.updated_count == 0

    # 재업로드: 기존 이름(A)은 update 경로, 신규(C)는 insert
    resp2 = UploadService.upload_colleges(
        db, [CollegeDataUpload(name="A"), CollegeDataUpload(name="C")]
    )
    assert resp2.uploaded_count == 1
    assert resp2.updated_count == 1
    assert db.query(College).count() == 3


def test_upload_courses_insert_and_intra_batch_dedup(db):
    rows = [
        CourseDataUpload(course_code="CSE101", course_name="개론", credits=3, course_year=1),
        CourseDataUpload(course_code="CSE101", course_name="개론(중복)", credits=3, course_year=1),
        CourseDataUpload(course_code="CSE102", course_name="프로그래밍", credits=3, course_year=1),
    ]
    resp = UploadService.upload_courses(db, rows)
    assert resp.success
    assert resp.uploaded_count == 2  # CSE101, CSE102
    assert resp.updated_count == 1   # 배치 내 두 번째 CSE101
    assert db.query(Course).count() == 2


def test_upload_courses_updates_existing_and_counts_batch_dupes(db):
    """이미 존재하는 과목을 배치에서 두 번 갱신 — 첫 등장 + 배치 중복 모두 update로 카운트."""
    db.add(
        Course(
            course_code="CSE101",
            course_name="old",
            credits=3,
            course_year=1,
            semester=1,
        )
    )
    db.commit()

    rows = [
        CourseDataUpload(course_code="CSE101", course_name="new1", credits=3, course_year=1),
        CourseDataUpload(course_code="CSE101", course_name="new2", credits=3, course_year=1),
    ]
    resp = UploadService.upload_courses(db, rows)
    assert resp.uploaded_count == 0
    assert resp.updated_count == 2
    assert db.query(Course).count() == 1
    assert db.query(Course).filter(Course.course_code == "CSE101").first().course_name == "new2"


# ---------------------------------------------------------------------------
# 대량평가 오케스트레이션 책임
# ---------------------------------------------------------------------------


def test_bulk_evaluate_derives_admission_year_and_counts(db, monkeypatch):
    _seed_department(db, 101, "C1", "D1")
    _seed_department(db, 102, "C2", "D2")
    _seed_student(db, 202400001, 101)
    _seed_student(db, 202500002, 101)

    calls = []

    def fake_eval(self, student_id, department_id, admission_year, save_to_db=False):
        calls.append((student_id, department_id, admission_year))
        return {"overall_score": 50.0}

    monkeypatch.setattr(eval_mod.EvaluationService, "evaluate_student", fake_eval)

    resp = EvaluationAdminService.bulk_evaluate(db, BulkEvaluationRequest(force_recalculate=True))

    assert resp.success
    assert resp.total_students == 2
    assert resp.total_departments == 2
    assert resp.success_count == 4
    assert resp.error_count == 0
    assert len(calls) == 4  # 2 학생 × 2 학과 (force_recalculate)

    years = {sid: yr for sid, _dept, yr in calls}
    assert years[202400001] == 2024  # 학번 앞 4자리
    assert years[202500002] == 2025


def test_bulk_evaluate_uses_cache_when_not_forced(db, monkeypatch):
    _seed_department(db, 101, "C1", "D1")
    _seed_student(db, 202400001, 101)
    db.add(
        StudentRequirementStatus(
            student_id=202400001, department_id=101, overall_score=88.0, is_satisfied=True
        )
    )
    db.commit()

    calls = []
    monkeypatch.setattr(
        eval_mod.EvaluationService,
        "evaluate_student",
        lambda self, **k: calls.append(k) or {"overall_score": 1.0},
    )

    resp = EvaluationAdminService.bulk_evaluate(db, BulkEvaluationRequest(force_recalculate=False))

    assert resp.success
    assert resp.success_count == 1
    assert calls == []  # 캐시 존재 → 평가 호출 안 함


# ---------------------------------------------------------------------------
# 캐시 관리 책임
# ---------------------------------------------------------------------------


def test_cached_evaluation_stats(db):
    _seed_department(db, 101, "C1", "D1")
    _seed_student(db, 202400001, 101)
    db.add(
        StudentRequirementStatus(
            student_id=202400001,
            department_id=101,
            overall_score=70,
            is_satisfied=True,
            calculated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    stats = EvaluationAdminService.get_cached_evaluation_stats(db)
    assert stats.total_cached == 1
    assert stats.cached_by_department.get("D1") == 1


def test_clear_and_delete_all(db):
    _seed_department(db, 101, "C1", "D1")
    _seed_student(db, 202400001, 101)
    db.add(
        StudentRequirementStatus(
            student_id=202400001, department_id=101, overall_score=70, is_satisfied=True
        )
    )
    db.commit()

    cleared = EvaluationAdminService.clear_cached_evaluations(db)
    assert cleared["success"]
    assert cleared["deleted_count"] == 1
    assert db.query(StudentRequirementStatus).count() == 0

    deleted = AdminService.delete_all_data(db)
    assert deleted["success"]
    assert db.query(Student).count() == 0
    assert db.query(Department).count() == 0


def test_bulk_evaluate_instantiates_evaluation_service_once(db, monkeypatch):
    """[벤치마크 B] EvaluationService는 배치 루프 밖에서 1회만 생성돼야 한다.

    이전에는 학생×학과마다 재생성되어(2×2=4회) 인스턴스 캐시가 매번 폐기됐다.
    """
    _seed_department(db, 101, "C1", "D1")
    _seed_department(db, 102, "C2", "D2")
    _seed_student(db, 202400001, 101)
    _seed_student(db, 202400002, 101)

    init_count = {"n": 0}
    orig_init = eval_mod.EvaluationService.__init__

    def counting_init(self, session):
        init_count["n"] += 1
        orig_init(self, session)

    monkeypatch.setattr(eval_mod.EvaluationService, "__init__", counting_init)
    monkeypatch.setattr(
        eval_mod.EvaluationService,
        "evaluate_student",
        lambda self, **k: {"overall_score": 1.0},
    )

    EvaluationAdminService.bulk_evaluate(db, BulkEvaluationRequest(force_recalculate=True))

    assert init_count["n"] == 1  # 4회가 아니라 1회
