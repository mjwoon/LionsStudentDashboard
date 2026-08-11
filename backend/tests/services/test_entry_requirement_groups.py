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
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _seed(s):
    s.add(Department(id=1, code="ELEC", name="전자공학부"))
    for code in ("ELE3037", "GEN2052"):
        s.add(Course(course_code=code, course_name=code, credits=3, course_year=1, semester=1))
    s.add(DepartmentEntryRequirement(
        id=1, department_id=1, admission_year=2026, requirement_group=1,
        target_grade_level=GradeLevelEnum.A, required_count=1, requirement_text="t",
    ))
    s.add(DepartmentEntryRequirement(
        id=2, department_id=1, admission_year=2026, requirement_group=2,
        target_grade_level=GradeLevelEnum.B, required_count=2, requirement_text="t",
    ))
    s.add(RequirementCourse(id=1, requirement_id=1, course_code="ELE3037"))
    s.add(RequirementCourse(id=2, requirement_id=2, course_code="ELE3037"))
    s.add(RequirementCourse(id=3, requirement_id=2, course_code="GEN2052"))
    s.commit()


def test_groups_expose_target_min_and_candidates(session):
    _seed(session)
    svc = EvaluationService(db=session)
    groups = {g["group"]: g for g in svc._get_entry_requirement_groups(1, admission_year=2026)}

    assert groups[1]["target_min"] == 4.0        # A
    assert groups[1]["required_count"] == 1
    assert groups[1]["candidate_codes"] == {"ELE3037"}
    assert groups[2]["target_min"] == 3.0        # B
    assert groups[2]["required_count"] == 2
    assert groups[2]["candidate_codes"] == {"ELE3037", "GEN2052"}
