"""
Student service for managing student data and GPA calculations.
"""

from sqlalchemy.orm import Session
from typing import Tuple
from models.models import Student, StudentCourse, Course


def calculate_student_gpa_and_credits(db: Session, student_id: str) -> Tuple[float, int]:
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
    course_ids = [e.course_id for e in enrollments]
    courses = db.query(Course).filter(Course.course_id.in_(course_ids)).all()
    course_credits = {c.course_id: c.credits for c in courses}
    
    # Calculate weighted GPA (excluding F grades from GPA calculation)
    total_grade_points = 0.0
    total_gpa_credits = 0
    total_earned_credits = 0
    
    for enrollment in enrollments:
        credits = course_credits.get(enrollment.course_id, DEFAULT_CREDITS)
        
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


def update_student_gpa(db: Session, student_id: str) -> Tuple[float, int]:
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


def refresh_all_student_gpas(db: Session) -> int:
    """
    Refresh GPA and credits for all students in the database.
    Useful for batch updates or data migration.
    
    Args:
        db: Database session
        
    Returns:
        int: Number of students updated
    """
    students = db.query(Student).all()
    
    for student in students:
        update_student_gpa(db, student.student_id)
    
    db.commit()
    
    return len(students)


def calculate_first_year_completion(
    db: Session,
    student_id: str,
    department_id: int
) -> Tuple[int, int]:
    """
    Calculate first-year course completion for a student in a specific department.
    
    Args:
        db: Database session
        student_id: Student PK (student_id VARCHAR)
        department_id: Department ID to check courses for
        
    Returns:
        Tuple[int, int]: (completed_count, total_count)
    """
    from constants import FIRST_YEAR, FAILING_GRADE
    
    # Get all first-year courses for the department
    first_year_courses = db.query(Course).filter(
        Course.course_department == department_id,
        Course.course_year == FIRST_YEAR
    ).all()
    
    if not first_year_courses:
        return 0, 0
    
    total_count = len(first_year_courses)
    first_year_course_ids = [c.course_id for c in first_year_courses]
    
    # Count completed courses (excluding F grades)
    completed_count = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.course_id.in_(first_year_course_ids),
        StudentCourse.grade.isnot(None),
        StudentCourse.grade != FAILING_GRADE
    ).count()
    
    return completed_count, total_count


def get_student_grade_summary(db: Session, student_id: str) -> dict:
    """
    Get comprehensive grade summary for a student.
    
    Args:
        db: Database session
        student_id: Student PK (student_id VARCHAR)
        
    Returns:
        dict: Summary including GPA, credits, grade distribution, etc.
    """
    from constants import FAILING_GRADE
    
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        return None
    
    # Get all enrollments with grades
    enrollments = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.grade.isnot(None),
        StudentCourse.grade != ""
    ).all()
    
    # Grade distribution
    grade_counts = {}
    for enrollment in enrollments:
        grade = enrollment.grade
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    
    # Course type distribution
    course_ids = [e.course_id for e in enrollments]
    courses = db.query(Course).filter(Course.course_id.in_(course_ids)).all()
    course_type_credits = {}
    
    for course in courses:
        course_type = course.course_type
        # Find enrollment for this course
        enrollment = next((e for e in enrollments if e.course_id == course.course_id), None)
        if enrollment and enrollment.grade != FAILING_GRADE:
            course_type_credits[course_type] = course_type_credits.get(course_type, 0) + course.credits
    
    return {
        "student_id": student.student_id,
        "name": student.name,
        "current_gpa": student.current_gpa,
        "total_credits": student.total_credits,
        "total_courses": len(enrollments),
        "grade_distribution": grade_counts,
        "credits_by_course_type": course_type_credits
    }
