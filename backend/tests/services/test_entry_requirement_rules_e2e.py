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


def _seed_elec(s):
    s.add(Department(id=1, code="ELEC", name="전자공학부"))
    for code in ("A_ONLY", "B1", "B2"):
        s.add(Course(course_code=code, course_name=code, credits=3, course_year=1, semester=1))
    # group1: A(4.0), 1 course among {A_ONLY}; group2: B(3.0), 2 courses among {B1,B2}
    s.add(DepartmentEntryRequirement(id=1, department_id=1, admission_year=2026,
          requirement_group=1, target_grade_level=GradeLevelEnum.A, required_count=1, requirement_text="t"))
    s.add(DepartmentEntryRequirement(id=2, department_id=1, admission_year=2026,
          requirement_group=2, target_grade_level=GradeLevelEnum.B, required_count=2, requirement_text="t"))
    s.add(RequirementCourse(id=1, requirement_id=1, course_code="A_ONLY"))
    s.add(RequirementCourse(id=2, requirement_id=2, course_code="B1"))
    s.add(RequirementCourse(id=3, requirement_id=2, course_code="B2"))
    s.commit()


def _completed(details):
    return {"codes": {d["course_code"] for d in details},
            "names": {d["course_name"] for d in details},
            "details": details}


def _d(code, numeric):
    return {"course_code": code, "course_name": code, "grade": "", "credits": 3, "numeric_grade": numeric}


def test_group1_satisfied_by_single_A(session):
    _seed_elec(session)
    svc = EvaluationService(db=session)
    completed = _completed([_d("A_ONLY", 4.0)])       # group1 satisfied
    assert svc._calculate_entry_requirement_score(completed, 1, 2026) == 100.0


def test_group2_partial_one_of_two_B(session):
    _seed_elec(session)
    svc = EvaluationService(db=session)
    completed = _completed([_d("B1", 3.0)])           # group1 0%, group2 50% -> OR max 50
    assert svc._calculate_entry_requirement_score(completed, 1, 2026) == 50.0
