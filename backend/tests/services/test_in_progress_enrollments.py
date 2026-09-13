"""성적이 아직 없는 수강 이력을 '듣는 중'으로 수집한다.

예전에는 `if e.grade and e.grade != FAILING_GRADE` 필터가 성적 없는 행을 통째로
버렸다. 2학기 수강이 전부 여기 해당해서 학생이 실제로 들은 과목의 절반가량이
평가에서 사라졌다. 버리지 않고 별도 상태로 표시해 내려보낸다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import Base, Course, StudentCourse
from services.evaluation_service import EvaluationService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def svc(session):
    for code, name in [("X", "엑스"), ("Y", "와이"), ("Z", "제트")]:
        session.add(Course(course_code=code, course_name=name, credits=3, course_year=1, semester=1))
    session.commit()
    return EvaluationService(db=session)


def _enr(code, grade, numeric, semester=1):
    return StudentCourse(
        student_id=1, course_code=code, grade=grade,
        numeric_grade=numeric, year=2026, semester=semester,
    )


def test_ungraded_enrollment_is_kept_as_in_progress(svc):
    result = svc._get_student_completed_courses([_enr("X", None, None, semester=2)])
    assert "X" in result["codes"]
    assert "엑스" in result["names"]
    detail = result["details"][0]
    assert detail["in_progress"] is True
    assert detail["numeric_grade"] is None


def test_graded_enrollment_is_not_in_progress(svc):
    result = svc._get_student_completed_courses([_enr("X", "A", 4.0)])
    assert result["details"][0]["in_progress"] is False
    assert result["details"][0]["numeric_grade"] == 4.0


def test_failing_grade_is_still_excluded(svc):
    """F는 '듣는 중'이 아니라 낙제다 — 기존대로 이수에서 뺀다."""
    result = svc._get_student_completed_courses([_enr("X", "F", 0.0)])
    assert result["codes"] == set()


def test_graded_wins_when_same_course_appears_twice(svc):
    """같은 과목을 재수강 중이면 성적이 나온 쪽을 남긴다(듣는 중이 덮어쓰지 않는다)."""
    result = svc._get_student_completed_courses([
        _enr("X", "B", 3.0, semester=1),
        _enr("X", None, None, semester=2),
    ])
    details = [d for d in result["details"] if d["course_code"] == "X"]
    assert len(details) == 1
    assert details[0]["in_progress"] is False
    assert details[0]["numeric_grade"] == 3.0


def test_mixed_enrollments_are_all_collected(svc):
    result = svc._get_student_completed_courses([
        _enr("X", "A", 4.0),
        _enr("Y", None, None, semester=2),
        _enr("Z", "F", 0.0),
    ])
    assert result["codes"] == {"X", "Y"}
    by_code = {d["course_code"]: d for d in result["details"]}
    assert by_code["X"]["in_progress"] is False
    assert by_code["Y"]["in_progress"] is True


# ── 수집 이전 단계: 조회 쿼리가 먼저 버리지 않는지 ──────────────────
# _get_student_completed_courses를 아무리 고쳐도, 그 앞의 SELECT가 성적 없는 행을
# 제외하면 아무 소용이 없다. 실제로 그렇게 되어 있었다.

import pytest as _pytest  # noqa: E402

from lions_core.models import (  # noqa: E402
    College, Department, DepartmentEntryRequirement, RequirementCourse, Student,
)


def _seed_requirement_dept(session):
    session.add(College(id=1, name="공과대학"))
    session.add(Department(id=204, college_id=1, name="전자공학부", code="ELEC"))
    session.add(Student(student_id=2026000001, name="테스트",
                        email="t@example.com", phone="010-0000-0000",
                        department_id=204))
    for code, name in [("GEN2053", "미분적분학2")]:
        session.add(Course(course_code=code, course_name=name, credits=3, course_year=1, semester=1))
    session.flush()
    req = DepartmentEntryRequirement(
        department_id=204, admission_year=2026, requirement_group=1,
        target_grade_level="A", required_count=1, requirement_text="A 1과목",
    )
    session.add(req)
    session.flush()
    session.add(RequirementCourse(requirement_id=req.id, course_code="GEN2053"))
    session.commit()


def test_evaluation_sees_ungraded_enrollment(session):
    """조회 쿼리가 성적 없는 수강을 걸러내면 '수강중'을 셀 수 없다."""
    _seed_requirement_dept(session)
    session.add(StudentCourse(
        student_id=2026000001, course_code="GEN2053", course_name="미분적분학2",
        completion_type="전공기초", grade=None, numeric_grade=None, year=2026, semester=2,
    ))
    session.commit()

    svc = EvaluationService(db=session)
    result = svc.evaluate_student(2026000001, 204, admission_year=2026)
    er = result["analysis_json"]["entry_requirement"]

    assert er["in_progress_courses"] == 1
    assert er["completed_courses"] == 0     # 성적이 없으니 충족은 아니다
    assert er["gate"] == "pending"          # 아직 진행 전 — 차단이 아니다
