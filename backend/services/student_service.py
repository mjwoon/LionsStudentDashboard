"""
Student service for managing student data and GPA calculations.
"""

from sqlalchemy.orm import Session
from typing import Tuple
from models.models import Student, StudentCourse, Course


def calculate_student_gpa_and_credits(db: Session, student_id: int) -> Tuple[float, int]:
    """
    Calculate student's GPA and total credits from their enrollments.
    
    Args:
        db: Database session
        student_id: Student PK (student_id VARCHAR)
        
    Returns:
        Tuple[float, int]: (current_gpa, total_credits)
    """
    from constants import FAILING_GRADE, DEFAULT_CREDITS
    
    # Get all completed enrollments with grades (exclude F and in-progress courses)
    enrollments = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.grade.isnot(None),
        StudentCourse.grade != ""
    ).all()
    
    if not enrollments:
        return 0.0, 0
    
    # Get course information for credits
    course_codes = [e.course_code for e in enrollments]
    courses = db.query(Course).filter(Course.course_code.in_(course_codes)).all()
    course_credits = {c.course_code: c.credits for c in courses}
    
    # Calculate weighted GPA (excluding F grades from GPA calculation)
    total_grade_points = 0.0
    total_gpa_credits = 0
    total_earned_credits = 0
    
    for enrollment in enrollments:
        credits = course_credits.get(enrollment.course_code, DEFAULT_CREDITS)
        
        # Total earned credits (including F)
        if enrollment.grade != FAILING_GRADE:
            total_earned_credits += credits
        
        # GPA calculation (exclude F grades)
        if enrollment.numeric_grade is not None and enrollment.grade != FAILING_GRADE:
            # Convert Decimal to float for calculation
            numeric_grade_float = float(enrollment.numeric_grade)
            total_grade_points += numeric_grade_float * credits
            total_gpa_credits += credits
    
    # Calculate GPA
    current_gpa = round(total_grade_points / total_gpa_credits, 2) if total_gpa_credits > 0 else 0.0
    
    return current_gpa, total_earned_credits

def update_student_gpa(db: Session, student_id: int) -> Tuple[float, int]:
    """
    Update student's current_gpa and total_credits fields.
    
    Args:
        db: Database session
        student_id: Student PK (student_id VARCHAR)
        
    Returns:
        Tuple[float, int]: Updated (current_gpa, total_credits)
    """
    gpa, credits = calculate_student_gpa_and_credits(db, student_id)
    
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if student:
        student.current_gpa = gpa
        student.total_credits = credits
        db.flush()
    
    return gpa, credits

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

