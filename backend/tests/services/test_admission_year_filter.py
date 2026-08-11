"""
Phase 7a — 진입요건이 학생 입학년도(admission_year)로 필터링되는지 검증.

이전에는 학과의 모든 연도 요건을 합산했다(admission_year 파라미터가 불활성).
이제 admission_year가 주어지면 해당 연도 룰셋만 적용한다.

인메모리 SQLite로 실제 쿼리 동작을 검증한다(mock이 아닌 real behavior).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import (
    Base, Department, Course,
    DepartmentEntryRequirement, RequirementCourse, GradeLevelEnum,
)
from services.evaluation_service import EvaluationService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _seed_two_year_requirements(s):
    """같은 학과·같은 그룹에 2024/2025 두 연도의 서로 다른 필수과목을 심는다."""
    s.add(Department(id=1, code="CS", name="컴퓨터학부"))
    s.add(Course(course_code="Y2024", course_name="2024전용과목",
                 credits=3, course_year=1, semester=1))
    s.add(Course(course_code="Y2025", course_name="2025전용과목",
                 credits=3, course_year=1, semester=1))

    s.add(DepartmentEntryRequirement(
        id=1, department_id=1, admission_year=2024, requirement_group=1,
        target_grade_level=GradeLevelEnum.C, required_count=1, requirement_text="2024 요건",
    ))
    s.add(DepartmentEntryRequirement(
        id=2, department_id=1, admission_year=2025, requirement_group=1,
        target_grade_level=GradeLevelEnum.C, required_count=1, requirement_text="2025 요건",
    ))
    s.add(RequirementCourse(id=1, requirement_id=1, course_code="Y2024"))
    s.add(RequirementCourse(id=2, requirement_id=2, course_code="Y2025"))
    s.commit()


def test_requirements_filtered_by_admission_year(session):
    _seed_two_year_requirements(session)
    svc = EvaluationService(db=session)

    got = svc._get_department_courses(1, admission_year=2024)
    codes = {c["course_code"] for c in got["necessary_courses"]}
    assert codes == {"Y2024"}  # 2025 요건은 제외


def test_no_admission_year_returns_all_years(session):
    """admission_year 미지정 시 레거시 호환: 모든 연도 요건 합산."""
    _seed_two_year_requirements(session)
    svc = EvaluationService(db=session)

    got = svc._get_department_courses(1)  # admission_year=None
    codes = {c["course_code"] for c in got["necessary_courses"]}
    assert codes == {"Y2024", "Y2025"}


def test_entry_requirement_score_uses_admission_year(session):
    """점수 경로도 연도 필터를 반영: 2024 학생이 Y2024 이수 → 100%."""
    _seed_two_year_requirements(session)
    svc = EvaluationService(db=session)

    completed = {
        "codes": {"Y2024"},
        "names": {"2024전용과목"},
        "details": [{"course_code": "Y2024", "course_name": "2024전용과목", "grade": "A", "credits": 3}],
    }
    # 2024 기준: 필수 1개(Y2024) 이수 → 100
    assert svc._calculate_entry_requirement_score(completed, 1, 2024) == 100.0
    # 2025 기준: 필수 1개(Y2025) 미이수 → 0
    assert svc._calculate_entry_requirement_score(completed, 1, 2025) == 0.0
