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


def test_completed_details_include_numeric_grade(session):
    session.add(Course(course_code="X", course_name="xx", credits=3, course_year=1, semester=1))
    session.add(Course(course_code="Y", course_name="yy", credits=3, course_year=1, semester=1))
    session.commit()
    svc = EvaluationService(db=session)

    enrollments = [
        StudentCourse(student_id=1, course_code="X", grade="A+", numeric_grade=4.5, year=2026, semester=1),
        StudentCourse(student_id=1, course_code="Y", grade="B", numeric_grade=None, year=2026, semester=1),
    ]
    details = {d["course_code"]: d for d in svc._get_student_completed_courses(enrollments)["details"]}

    assert details["X"]["numeric_grade"] == 4.5           # from StudentCourse.numeric_grade
    assert details["Y"]["numeric_grade"] == 3.0           # fallback GRADE_TO_NUMERIC["B"]
