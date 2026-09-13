"""전공이수체계도(교육과정 표)가 내려보내는 이수 상태와 학기.

화면에서 두 가지가 틀리게 보였다.
  - F(낙제)가 '이수완료 (F)'로 표시됐다. 표는 성적을 보지 않고 수강 이력 유무만 봤다.
  - 모든 과목이 1학기로 표시됐다. 표가 과목 마스터의 학기를 쓰는데 그 값이 전부 1이었다.
둘 다 점수 계산과 어긋나 있었다 — 점수는 F를 빼고, 학기는 교육과정에 제대로 들어 있다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import (
    Base, College, Course, Curriculum, Department, Student, StudentCourse,
)
from services.evaluation_service import EvaluationService

DEPT = 700


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(College(id=7, name="테스트대학"))
    s.add(Department(id=DEPT, college_id=7, name="테스트학과", code="TEST"))
    s.add(Student(student_id=2026000001, name="테스트", email="t@example.com",
                  phone="010-0000-0000", department_id=DEPT))
    # 과목 마스터의 학기는 신뢰할 수 없다(업로드가 채우지 못해 전부 1이었다).
    for code, name in [("AAA1001", "가"), ("BBB1002", "나"), ("CCC1003", "다"), ("DDD1004", "라")]:
        s.add(Course(course_code=code, course_name=name, credits=3,
                     course_type="전공기초", course_department="테스트학과",
                     course_year=1, semester=1))
    # 교육과정에는 1·2학기가 제대로 들어 있다.
    for code, name, sem in [("AAA1001", "가", 1), ("BBB1002", "나", 2),
                            ("CCC1003", "다", 2), ("DDD1004", "라", 1)]:
        s.add(Curriculum(department_id=DEPT, course_year=1, course_code=code,
                         course_name=name, credits=3, course_type="전공기초", semester=sem))
    s.commit()
    yield s
    s.close()


def _enr(session, code, name, grade, numeric, semester=1):
    session.add(StudentCourse(student_id=2026000001, course_code=code, course_name=name,
                              completion_type="전공기초", grade=grade, numeric_grade=numeric,
                              year=2026, semester=semester))
    session.commit()


def _by_code(session):
    details = EvaluationService(db=session).get_curriculum_details(2026000001, DEPT)
    return {c["course_code"]: c for c in details.get(1, [])}


# ── 이수 상태: F는 이수가 아니다 ────────────────────────────────────

def test_failed_course_is_not_completed(session):
    _enr(session, "AAA1001", "가", "F", 0.0)
    assert _by_code(session)["AAA1001"]["completion_status"] == "failed"


def test_passed_course_is_completed(session):
    _enr(session, "AAA1001", "가", "B", 3.0)
    assert _by_code(session)["AAA1001"]["completion_status"] == "completed"


def test_ungraded_course_is_in_progress(session):
    _enr(session, "AAA1001", "가", None, None, semester=2)
    assert _by_code(session)["AAA1001"]["completion_status"] == "in_progress"


def test_untaken_course_is_not_taken(session):
    assert _by_code(session)["AAA1001"]["completion_status"] == "not_taken"


def test_failed_course_matches_the_score_side(session):
    """표가 F를 이수로 세면 점수(F 제외)와 어긋난다 — 같은 판정이어야 한다."""
    _enr(session, "AAA1001", "가", "F", 0.0)
    svc = EvaluationService(db=session)
    completed = svc._get_student_completed_courses(
        session.query(StudentCourse).filter(StudentCourse.student_id == 2026000001).all()
    )
    assert "AAA1001" not in completed["codes"]                       # 점수 쪽
    assert _by_code(session)["AAA1001"]["completion_status"] != "completed"  # 표 쪽


# ── 학기: 교육과정이 정답이다 ───────────────────────────────────────

def test_semester_comes_from_curriculum_not_course_master(session):
    """마스터는 전부 1학기지만 교육과정에는 2학기가 있다."""
    got = {code: c["semester"] for code, c in _by_code(session).items()}
    assert got == {"AAA1001": 1, "BBB1002": 2, "CCC1003": 2, "DDD1004": 1}


def test_second_semester_courses_are_not_all_collapsed(session):
    sems = {c["semester"] for c in _by_code(session).values()}
    assert sems == {1, 2}


# ── 과목 마스터 업로드가 학기를 버리고 있었다 ────────────────────────
# group3_courses.csv에 학기 열이 있는데 CourseDataUpload에 필드가 없어
# `getattr(data, 'semester', None) or 1` 이 전부 1로 만들어 버렸다.

from models.schemas.uploads import CourseDataUpload  # noqa: E402
from services.upload_service import UploadService  # noqa: E402


def test_course_upload_keeps_semester(session):
    UploadService.upload_courses(session, [CourseDataUpload(**{
        "학수번호": "ZZZ9001", "교과목이름": "가을과목", "학점": 3,
        "이수구분": "전공기초", "학년": 1, "학기": 2, "설강학과": "테스트학과",
    })])
    saved = session.query(Course).filter(Course.course_code == "ZZZ9001").one()
    assert saved.semester == 2


def test_course_upload_defaults_semester_when_blank(session):
    """학기가 비어 있는 행(마스터 재구축분 다수)은 기존대로 1로 둔다."""
    UploadService.upload_courses(session, [CourseDataUpload(**{
        "학수번호": "ZZZ9002", "교과목이름": "학기없음", "학점": 3,
        "이수구분": "전공기초", "학년": 1, "설강학과": "테스트학과",
    })])
    saved = session.query(Course).filter(Course.course_code == "ZZZ9002").one()
    assert saved.semester == 1
