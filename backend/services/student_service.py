"""학생 데이터 서비스 — 진입요건 이수 집계."""

from sqlalchemy.orm import Session
from typing import Tuple
from models.models import StudentCourse


def calculate_entry_requirement_completion(
    db: Session,
    student_id: int,
    department_id: int
) -> Tuple[int, int]:
    """
    Calculate entry requirement course completion for a student in a specific department.

    Returns:
        Tuple[int, int]: (completed_count, total_count)
    """
    from constants import FAILING_GRADE
    from models.models import DepartmentEntryRequirement, RequirementCourse

    req_courses = db.query(RequirementCourse).join(
        DepartmentEntryRequirement,
        RequirementCourse.requirement_id == DepartmentEntryRequirement.id
    ).filter(
        DepartmentEntryRequirement.department_id == department_id
    ).all()

    if not req_courses:
        return 0, 0

    required_codes = list({rc.course_code for rc in req_courses})
    total_count = len(required_codes)

    completed_count = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.course_code.in_(required_codes),
        StudentCourse.grade.isnot(None),
        StudentCourse.grade != FAILING_GRADE
    ).count()

    return completed_count, total_count

