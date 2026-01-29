"""
Seed service for database population.

This module contains all the utility functions for seeding the database
with sample data, including GPA calculation, enrollment generation, and more.
"""

import time
import json
import os
import random
from typing import List, Dict, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from datetime import datetime

from models.database import (
    Student,
    Course,
    CourseEnrollment,
    MajorSurvey,
)
from fixtures.seed_config import (
    GRADE_OPTIONS,
    GRADE_PROFILE_WEIGHTS,
    MAX_CREDITS_PER_SEMESTER,
    DB_MAX_RETRIES,
    DB_RETRY_DELAY,
)


def calculate_student_gpa_and_credits(db: Session, student_id: int) -> Tuple[float, int]:
    """
    Calculate student's GPA and total credits from their enrollments.
    
    Args:
        db: Database session
        student_id: Student database ID
        
    Returns:
        Tuple[float, int]: (current_gpa, total_credits)
    """
    from constants import FAILING_GRADE, DEFAULT_CREDITS
    
    # Get all completed enrollments with grades (exclude F and in-progress courses)
    enrollments = db.query(CourseEnrollment).filter(
        CourseEnrollment.student_id == student_id,
        CourseEnrollment.grade.isnot(None),
        CourseEnrollment.grade != ""
    ).all()
    
    if not enrollments:
        return 0.0, 0
    
    # Get course information for credits
    course_ids = [e.course_id for e in enrollments]
    courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
    course_credits = {c.id: c.credits for c in courses}
    
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


def update_student_gpa(db: Session, student_id: int) -> None:
    """
    Update student's current_gpa and total_credits fields.
    
    Args:
        db: Database session
        student_id: Student database ID
    """
    gpa, credits = calculate_student_gpa_and_credits(db, student_id)
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        student.current_gpa = gpa
        student.total_credits = credits
        db.flush()


def generate_random_grade(grade_profile: str = "normal") -> Tuple[str, float]:
    """
    Generate a random grade with configurable bias based on student profile.
    
    Args:
        grade_profile: Grade distribution profile
            - "excellent": High achiever (mostly A grades)
            - "average": Average student (mostly B grades)
            - "struggling": Below average (mostly C-D grades)
            - "normal": Default distribution (good grade bias)
    
    Returns:
        Tuple[str, float]: (grade letter, numeric grade)
    """
    weights = GRADE_PROFILE_WEIGHTS.get(grade_profile, GRADE_PROFILE_WEIGHTS["normal"])
    grade, numeric = random.choices(GRADE_OPTIONS, weights=weights, k=1)[0]
    return grade, numeric


def wait_for_db(session_factory, max_retries: int = DB_MAX_RETRIES, delay: int = DB_RETRY_DELAY) -> bool:
    """
    Wait for database connection to be ready.
    
    Args:
        session_factory: SQLAlchemy session factory
        max_retries: Maximum number of connection attempts
        delay: Delay in seconds between retries
        
    Returns:
        bool: True if connected successfully, False otherwise
    """
    for i in range(max_retries):
        try:
            db = session_factory()
            db.execute(text("SELECT 1"))
            db.close()
            print("Database is ready!")
            return True
        except OperationalError:
            print(f"Database not ready, waiting... ({i+1}/{max_retries})")
            time.sleep(delay)
    print("Database connection timeout!")
    return False


def load_json_data(filename: str) -> dict:
    """
    Load JSON data from the data directory.
    
    Args:
        filename: Name of the JSON file (e.g., 'sw.json')
        
    Returns:
        dict: Loaded JSON data
    """
    # Get the backend directory (parent of fixtures)
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(backend_dir, "data", filename)
    
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_course_enrollments(
    student_id: int,
    courses_by_semester: Dict[int, List[Dict]],
    year: int,
    max_credits: int = MAX_CREDITS_PER_SEMESTER,
    include_grades: bool = True,
    shuffle_courses: bool = True,
    grade_profile: str = "normal"
) -> List[CourseEnrollment]:
    """
    Create course enrollments for a student across multiple semesters.
    
    Args:
        student_id: Student database ID
        courses_by_semester: Dict mapping semester number to list of course info dicts
        year: Academic year
        max_credits: Maximum credits allowed per semester
        include_grades: Whether to include grades (False for ongoing semesters)
        shuffle_courses: Whether to randomize course selection order
        grade_profile: Grade distribution profile for this student
        
    Returns:
        List[CourseEnrollment]: List of enrollment objects
    """
    enrollments = []
    
    for semester, courses in courses_by_semester.items():
        sem_credits = 0
        course_list = courses.copy()
        if shuffle_courses:
            random.shuffle(course_list)
        
        for course_info in course_list:
            if sem_credits + course_info["credits"] <= max_credits:
                # Determine if grades should be included
                # 2026년 1학기는 현재 진행중이므로 성적 없음 (현재: 2026년 1월)
                should_include_grade = include_grades and not (year == 2026 and semester == 1)
                
                if should_include_grade:
                    grade, numeric_grade = generate_random_grade(grade_profile)
                else:
                    grade, numeric_grade = None, None
                
                enrollment = CourseEnrollment(
                    student_id=student_id,
                    course_id=course_info["id"],
                    year=year,
                    semester=semester,
                    completion_type=course_info["course_type"],
                    is_retake=False,
                    grade=grade,
                    numeric_grade=numeric_grade,
                )
                enrollments.append(enrollment)
                sem_credits += course_info["credits"]
    
    return enrollments


def create_survey_for_student(
    student_id: int,
    round_id: int,
    first_choice_dept: int,
    decision_scale: int,
    round_year: int,
    round_month: int,
    second_choice_dept: Optional[int] = None
) -> MajorSurvey:
    """
    Create a major survey entry for a student.
    
    Args:
        student_id: Student database ID
        round_id: Survey round ID
        first_choice_dept: First choice department ID
        decision_scale: Decision certainty (1-5)
        round_year: Year of the survey round
        round_month: Month of the survey round
        second_choice_dept: Optional second choice department ID
        
    Returns:
        MajorSurvey: Survey object
    """
    # Determine decision status based on scale
    if decision_scale >= 4:
        decision_status_id = 1  # 최종결정
    elif decision_scale >= 3:
        decision_status_id = 2  # 고민중
    else:
        decision_status_id = 3  # 조사중
    
    return MajorSurvey(
        student_id=student_id,
        round_id=round_id,
        first_choice_dept_id=first_choice_dept,
        second_choice_dept_id=second_choice_dept,
        decision_status_id=decision_status_id,
        decision_scale=decision_scale,
        submitted_at=datetime(round_year, round_month, random.randint(1, 28))
    )
