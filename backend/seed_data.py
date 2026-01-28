"""
Seed script to populate the database with sample data
Run this script to create initial test data

This script creates:
- 300 regular students + 3 special test students
- Courses from multiple departments (CS, Data Intelligence, Design Convergence, Architecture)
- Course enrollments with realistic grade distributions
- Survey responses across 3 rounds
- Department entry requirements
"""

import time
import json
import os
import random
from typing import List, Dict, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from database import SessionLocal, init_db
from models.database import (
    College,
    Department,
    Advisor,
    Student,
    Course,
    CourseEnrollment,
    SurveyRound,
    MajorSurvey,
    DecisionStatus,
    DepartmentEntryRequirement,
    RequirementCourse,
    StudentRequirementStatus,
    GradeLevelEnum,
)
from datetime import datetime, timedelta

# ============================================================================
# CONSTANTS
# ============================================================================

# Department IDs
DEPT_LIONS_COLLEGE = 100
DEPT_COMPUTER_SCIENCE = 300
DEPT_DATA_INTELLIGENCE = 303
DEPT_DESIGN_CONVERGENCE = 304
DEPT_ARCHITECTURE = 200

# Academic Settings
MAX_CREDITS_PER_SEMESTER = 20
TARGET_ADDITIONAL_ENROLLMENTS = 2000
REGULAR_STUDENT_COUNT = 300

# Grade Options and Weights
GRADE_OPTIONS = [
    ('A+', 4.5), ('A0', 4.0), 
    ('B+', 3.3), ('B0', 3.0), 
    ('C+', 2.3), ('C0', 2.0), 
    ('D+', 1.3), ('D0', 1.0), 
    ('F', 0.0)
]
GRADE_WEIGHTS = [15, 20, 12, 15, 8, 6, 5, 3, 2]  # 9개로 맞춤 (합계: 86)

# Special Students Configuration (for testing and demos)
# These students have fixed, reproducible data for consistent testing
SPECIAL_STUDENTS_CONFIG = [
    {
        "student_id": "2025123001",
        "name": "강우수",  # Excellent student (우수 = excellent)
        "email": "kim.woosoo@hanyang.ac.kr",
        "phone": "010-1111-1111",
        "track": "자연계열",
        "pride": "O",
        "class_number": 6,
        "advisor_id": 2,
        "target_dept": DEPT_DATA_INTELLIGENCE,
        "decision_scale": 5,  # 매우 확실 - 성적 우수, 목표 명확
        "grade_seed": 1001,  # Random seed for reproducible grades
        "grade_profile": "excellent",  # High achiever (mostly A grades)
        "description": "High-performing student with clear career goals in Data Intelligence"
    },
    {
        "student_id": "2025123002",
        "name": "강보통",  # Average student (보통 = average)
        "email": "lee.botong@hanyang.ac.kr",
        "phone": "010-2222-2222",
        "track": "전계열",
        "pride": "S",
        "class_number": 10,
        "advisor_id": 2,
        "target_dept": DEPT_DATA_INTELLIGENCE,
        "decision_scale": 3,  # 보통 - 평범한 성적, 고민 중
        "grade_seed": 2002,  # Random seed for reproducible grades
        "grade_profile": "average",  # Average grades (B range)
        "description": "Average student exploring major options, considering Data Intelligence"
    },
    {
        "student_id": "2025123003",
        "name": "강고민",  # Struggling student (고민 = worry/concern)
        "email": "park.gomin@hanyang.ac.kr",
        "phone": "010-3333-3333",
        "track": "인문사회계열",
        "pride": "O",
        "class_number": 6,
        "advisor_id": 1,
        "target_dept": DEPT_DESIGN_CONVERGENCE,
        "decision_scale": 2,  # 불확실 - 성적 부진, 진로 고민
        "grade_seed": 3003,  # Random seed for reproducible grades
        "grade_profile": "struggling",  # Lower grades (C-D range)
        "description": "Student facing academic challenges, uncertain about major choice"
    },
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_student_gpa_and_credits(db: Session, student_id: int) -> Tuple[float, int]:
    """
    Calculate student's GPA and total credits from their enrollments.
    
    Args:
        db: Database session
        student_id: Student database ID
        
    Returns:
        Tuple[float, int]: (current_gpa, total_credits)
    """
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
        credits = course_credits.get(enrollment.course_id, 3)  # Default to 3 if not found
        
        # Total earned credits (including F)
        if enrollment.grade != 'F':
            total_earned_credits += credits
        
        # GPA calculation (exclude F grades)
        if enrollment.numeric_grade is not None and enrollment.grade != 'F':
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
    if grade_profile == "excellent":
        # Excellent students: heavily weighted toward A grades
        weights = [25, 30, 15, 10, 8, 5, 3, 2, 2]  # 9개 (A+ 중심)
    elif grade_profile == "average":
        # Average students: mostly B grades with some A and C
        weights = [5, 8, 15, 20, 15, 10, 8, 5, 2]  # 9개 (B 중심)
    elif grade_profile == "struggling":
        # Struggling students: mostly C-D grades with some B
        weights = [1, 2, 5, 8, 12, 15, 15, 12, 5]  # 9개 (C-D 중심)
    else:  # "normal" - default good grade bias
        weights = GRADE_WEIGHTS
    
    grade, numeric = random.choices(GRADE_OPTIONS, weights=weights, k=1)[0]
    return grade, numeric


def wait_for_db(max_retries: int = 30, delay: int = 1) -> bool:
    """
    Wait for database connection to be ready.
    
    Args:
        max_retries: Maximum number of connection attempts
        delay: Delay in seconds between retries
        
    Returns:
        bool: True if connected successfully, False otherwise
    """
    for i in range(max_retries):
        try:
            db = SessionLocal()
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
    json_path = os.path.join(os.path.dirname(__file__), "data", filename)
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



# ============================================================================
# MAIN SEEDING FUNCTION
# ============================================================================

def seed_database():
    """
    Populate database with comprehensive sample data.
    
    Creates:
    - Colleges and Departments
    - Advisors
    - Students (300 regular + 3 special test students)
    - Courses (SW, Data Intelligence, Design Convergence, Architecture)
    - Course Enrollments with realistic distributions
    - Survey Rounds and Responses
    - Department Entry Requirements
    """
    # Wait for database to be ready
    if not wait_for_db():
        print("Failed to connect to database")
        return

    # Initialize database schema
    init_db()

    db = SessionLocal()

    try:
        # Clear existing data
        print("Clearing existing data...")
        db.query(StudentRequirementStatus).delete()
        db.query(RequirementCourse).delete()
        db.query(DepartmentEntryRequirement).delete()
        db.query(MajorSurvey).delete()
        db.query(DecisionStatus).delete()
        db.query(CourseEnrollment).delete()
        db.query(Course).delete()
        db.query(Student).delete()
        db.query(Advisor).delete()
        db.query(SurveyRound).delete()
        db.query(Department).delete()
        db.query(College).delete()
        db.commit()

        # Create Colleges
        print("Creating colleges...")
        college1 = College(id=1, name="라이언스 칼리지")
        college2 = College(id=2, name="공학대학")
        college3 = College(id=3, name="소프트웨어융합대학")
        college4 = College(id=4, name="첨단융합대학")
        college5 = College(id=5, name="경상대학")
        college6 = College(id=6, name="커뮤니케이션%컬쳐대학")
        college7 = College(id=7, name="글로벌문화통상대학")
        college8 = College(id=8, name="디자인대학")

        db.add_all(
            [
                college1,
                college2,
                college3,
                college4,
                college5,
                college6,
                college7,
                college8,
            ]
        )
        db.commit()

        # ====================================================================
        # DEPARTMENTS
        # ====================================================================
        print("Creating departments...")
        college_data = load_json_data("college.json")
        
        departments_list = []
        for dept_data in college_data["departments"]:
            department = Department(
                id=dept_data["id"],
                code=dept_data["code"],
                name=dept_data["name"],
                college_id=dept_data["college_id"],
                min_credits=dept_data.get("min_credits")
            )
            departments_list.append(department)

        db.add_all(departments_list)
        db.commit()
        print(f"Created {len(departments_list)} departments from college.json")

        # Create Advisors
        print("Creating advisors...")
        advisors = [
            # 라이언스 칼리지
            Advisor(id=1, name="박교수", email="park@hanyang.ac.kr", department_id=100),
            Advisor(id=2, name="최교수", email="choi@hanyang.ac.kr", department_id=100),
            Advisor(id=3, name="김교수", email="kim@hanyang.ac.kr", department_id=100),
            # 공과대학
            Advisor(
                id=4, name="이교수", email="lee.ee@hanyang.ac.kr", department_id=205
            ),  # 전자공학부
            Advisor(
                id=5, name="정교수", email="jung.me@hanyang.ac.kr", department_id=206
            ),  # 기계공학과
            Advisor(
                id=6, name="강교수", email="kang.chem@hanyang.ac.kr", department_id=207
            ),  # 배터리소재화학공학과
            # 소프트웨어융합대학
            Advisor(
                id=7, name="송교수", email="song.cs@hanyang.ac.kr", department_id=300
            ),  # 컴퓨터학부
            Advisor(
                id=8, name="윤교수", email="yoon.math@hanyang.ac.kr", department_id=306
            ),  # 수리데이터사이언스학과
            # 첨단융합대학
            Advisor(
                id=9, name="한교수", email="han.semi@hanyang.ac.kr", department_id=400
            ),  # 차세대반도체융합공학부
            Advisor(
                id=10, name="오교수", email="oh.bio@hanyang.ac.kr", department_id=403
            ),  # 바이오신양융합학부
            # 경상대학
            Advisor(
                id=11, name="서교수", email="seo.biz@hanyang.ac.kr", department_id=500
            ),  # 경영학부
            # 글로벌문화통상대학
            Advisor(
                id=12,
                name="안교수",
                email="ahn.global@hanyang.ac.kr",
                department_id=700,
            ),  # 글로벌문화통상학부
        ]

        db.add_all(advisors)
        db.commit()

        # ====================================================================
        # STUDENTS
        # ====================================================================
        print("Creating students...")
        random.seed(42)  # For reproducible test data

        first_names = [
            "민준", "서연", "예준", "하은", "지호", "서윤", "주원", "지우", "도윤", "서현",
            "시우", "수아", "건우", "민서", "현우", "지안", "준서", "채원", "지훈", "유나",
            "동현", "소율", "승우", "예은", "준혁", "다은", "현준", "시은", "민재", "하린",
            "태양", "별", "하늘", "바다", "달빛", "구름", "강물", "산들", "나무", "꽃잎",
        ]
        last_names = [
            "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
            "한", "오", "서", "신", "권", "황", "안", "송", "홍", "전",
        ]

        # Track distribution: 전계열(공대) 40%, 자연계열 30%, 인문사회계열 30%
        tracks = ["전계열"] * 40 + ["자연계열"] * 30 + ["인문사회계열"] * 30
        prides = ["L", "I", "O", "N", "S", "E"]

        students = []

        # Create regular students (all as 2025 freshmen in Lions College)
        for i in range(REGULAR_STUDENT_COUNT):
            name = random.choice(last_names) + random.choice(first_names)
            track = random.choice(tracks)
            students.append(
                Student(
                    student_id=f"2025{i:05d}",
                    name=name,
                    email=f"student{i:05d}@hanyang.ac.kr",
                    phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                    department_id=DEPT_LIONS_COLLEGE,
                    advisor_id=random.randint(1, 3),  # Lions College advisors
                    track=track,
                    pride=random.choice(prides),
                    class_number=random.randint(1, 10),
                    status="재학",
                )
            )

        db.add_all(students)
        db.flush()  # Assign IDs
        student_ids = [student.id for student in students]
        
        # Create special test students with fixed, reproducible data
        print(f"Creating {len(SPECIAL_STUDENTS_CONFIG)} special test students...")
        special_students = []
        for config in SPECIAL_STUDENTS_CONFIG:
            special_students.append(
                Student(
                    student_id=config["student_id"],
                    name=config["name"],
                    email=config["email"],
                    phone=config["phone"],
                    department_id=DEPT_LIONS_COLLEGE,
                    advisor_id=config["advisor_id"],
                    track=config["track"],
                    pride=config["pride"],
                    class_number=config["class_number"],
                    status="재학",
                )
            )
        
        db.add_all(special_students)
        db.flush()
        special_student_ids = [student.id for student in special_students]
        
        db.commit()
        print(f"Created {len(students)} regular students + {len(special_students)} special test students")

        # ====================================================================
        # COURSES
        # ====================================================================
        print("Creating courses...")

        # Load SW curriculum
        sw_data = load_json_data("sw.json")

        courses = []
        for idx, course_data in enumerate(sw_data["curriculum"], start=1):
            course = Course(
                id=idx,
                course_code=course_data["course_code"],
                course_name=course_data["course_name"],
                credits=course_data["credits"],
                course_type=course_data["course_type"],
                department_id=DEPT_COMPUTER_SCIENCE,
                course_year=course_data.get("course_year"),
                semester=course_data.get("semester"),
            )
            courses.append(course)

        db.add_all(courses)
        db.commit()
        print(f"Created {len(courses)} courses from sw.json")

        # ====================================================================
        # COURSE ENROLLMENTS - Regular Students
        # ====================================================================
        print("Creating course enrollments for regular students...")
        enrollments = []

        # Categorize 1st year courses by semester
        first_year_sem1_courses = [
            {"id": idx + 1, "credits": course["credits"], "course_type": course["course_type"]}
            for idx, course in enumerate(sw_data["curriculum"])
            if course["course_year"] == 1 and course["semester"] == 1
        ]
        first_year_sem2_courses = [
            {"id": idx + 1, "credits": course["credits"], "course_type": course["course_type"]}
            for idx, course in enumerate(sw_data["curriculum"])
            if course["course_year"] == 1 and course["semester"] == 2
        ]

        print(f"  - 1st year, 1st semester: {len(first_year_sem1_courses)} courses")
        print(f"  - 1st year, 2nd semester: {len(first_year_sem2_courses)} courses")

        # Assign courses to each regular student
        for idx, student_id in enumerate(student_ids):
            student_enrollments = create_course_enrollments(
                student_id=student_id,
                courses_by_semester={
                    1: first_year_sem1_courses,
                    2: first_year_sem2_courses
                },
                year=2025,
                max_credits=MAX_CREDITS_PER_SEMESTER,
                include_grades=True
            )
            enrollments.extend(student_enrollments)

            # Progress indicator
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(student_ids)} students...")

        print(f"Adding {len(enrollments)} enrollments to database...")
        db.add_all(enrollments)
        db.commit()
        print("Regular student enrollments created successfully!")
        
        # Update GPA and credits for all regular students
        print("Calculating GPA and total credits for regular students...")
        for idx, student_id in enumerate(student_ids):
            update_student_gpa(db, student_id)
            if (idx + 1) % 50 == 0:
                print(f"  Updated {idx + 1}/{len(student_ids)} students...")
        db.commit()
        print("Student GPA and credits updated successfully!")
        
        # ====================================================================
        # COURSE ENROLLMENTS - Special Test Students
        # ====================================================================
        print("Creating enrollments for special test students...")
        print("  - Using fixed course set and reproducible grade patterns")
        special_enrollments = []
        
        # Select fixed course set for consistency across special students
        # All special students take the SAME courses for direct comparison
        sem1_selected_courses = []
        sem1_total = 0
        for course_info in first_year_sem1_courses[:10]:
            if sem1_total + course_info["credits"] <= 18:
                sem1_selected_courses.append(course_info)
                sem1_total += course_info["credits"]
        
        sem2_selected_courses = []
        sem2_total = 0
        for course_info in first_year_sem2_courses[:10]:
            if sem2_total + course_info["credits"] <= 18:
                sem2_selected_courses.append(course_info)
                sem2_total += course_info["credits"]
        
        print(f"  - Fixed course set: {len(sem1_selected_courses)} in sem1, {len(sem2_selected_courses)} in sem2")
        
        # Each special student gets enrollments with their unique grade pattern
        for idx, config in enumerate(SPECIAL_STUDENTS_CONFIG):
            student_id = special_student_ids[idx]
            grade_profile = config["grade_profile"]
            grade_seed = config["grade_seed"]
            
            # Set random seed for reproducible grades
            random.seed(grade_seed)
            
            student_enrollments = create_course_enrollments(
                student_id=student_id,
                courses_by_semester={
                    1: sem1_selected_courses,
                    2: sem2_selected_courses
                },
                year=2025,
                max_credits=18,
                include_grades=True,
                grade_profile=grade_profile
            )
            special_enrollments.extend(student_enrollments)
            
            # Reset random seed to avoid affecting other random operations
            random.seed()
        
        print(f"Adding {len(special_enrollments)} special enrollments to database...")
        db.add_all(special_enrollments)
        db.commit()
        print("Special student enrollments created successfully!")
        print(f"  - 강우수 ({SPECIAL_STUDENTS_CONFIG[0]['description']})")
        print(f"  - 강보통 ({SPECIAL_STUDENTS_CONFIG[1]['description']})")
        print(f"  - 강고민 ({SPECIAL_STUDENTS_CONFIG[2]['description']})")
        
        # Update GPA and credits for special students
        print("Calculating GPA and total credits for special students...")
        for idx, student_id in enumerate(special_student_ids):
            update_student_gpa(db, student_id)
            student = db.query(Student).filter(Student.id == student_id).first()
            print(f"  - {student.name}: GPA {student.current_gpa:.2f}, Credits {student.total_credits}")
        db.commit()

        # ====================================================================
        # ADDITIONAL COURSES (Data Intelligence, Design Convergence, Architecture)
        # ====================================================================
        print("Loading additional department courses...")
        data_intelli_data = load_json_data("dataIntelli.json")
        design_converge_data = load_json_data("designConverge.json")
        arch_data = load_json_data("arch.json")
        necessary_data = load_json_data("necessary.json")
        
        # Track existing course codes to avoid duplicates (e.g., shared general education courses)
        existing_course_codes = {}
        for c in sw_data["curriculum"]:
            existing_course_codes[c["course_code"]] = (c["course_name"], c["credits"], c["course_type"], DEPT_COMPUTER_SCIENCE)
        
        # Consolidate additional courses from multiple departments
        additional_course_data = []
        
        # Add Data Intelligence courses (dept_id: 303)
        for course_info in data_intelli_data["curriculum"]:
            code = course_info["course_code"]
            if code in existing_course_codes:
                continue  # Skip duplicate courses
            
            additional_course_data.append({
                "course_code": code,
                "course_name": course_info["course_name"],
                "course_type": course_info["course_type"],
                "credits": course_info["credits"],
                "course_year": course_info["course_year"],
                "semester": course_info["semester"],
                "department_id": DEPT_DATA_INTELLIGENCE
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], DEPT_DATA_INTELLIGENCE)
        
        # Add Design Convergence courses (dept_id: 304)
        for course_info in design_converge_data["curriculum"]:
            code = course_info["course_code"]
            if code in existing_course_codes:
                continue
                
            additional_course_data.append({
                "course_code": code,
                "course_name": course_info["course_name"],
                "course_type": course_info["course_type"],
                "credits": course_info["credits"],
                "course_year": course_info["course_year"],
                "semester": course_info["semester"],
                "department_id": DEPT_DESIGN_CONVERGENCE
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], DEPT_DESIGN_CONVERGENCE)
        
        # Add Architecture courses (dept_id: 200)
        for course_info in arch_data["curriculum"]:
            code = course_info["course_code"]
            if code in existing_course_codes:
                continue
                
            additional_course_data.append({
                "course_code": code,
                "course_name": course_info["course_name"],
                "course_type": course_info["course_type"],
                "credits": course_info["credits"],
                "course_year": course_info["course_year"],
                "semester": course_info["semester"],
                "department_id": DEPT_ARCHITECTURE
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], DEPT_ARCHITECTURE)
        
        # Add courses from necessary.json (entry requirement courses)
        # These courses may not have department_id, so we use a general department (100 = Lions College)
        for college in necessary_data.get("colleges", []):
            for major in college.get("majors", []):
                for course_info in major.get("necessary_courses", []):
                    code = course_info["course_code"]
                    if code in existing_course_codes:
                        continue  # Skip if already exists
                    
                    additional_course_data.append({
                        "course_code": code,
                        "course_name": course_info["course_name"],
                        "course_type": course_info.get("course_type", "전공기초"),
                        "credits": course_info["credits"],
                        "course_year": course_info["course_year"],
                        "semester": course_info["semester"],
                        "department_id": DEPT_LIONS_COLLEGE  # General department for shared courses
                    })
                    existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info.get("course_type", "전공기초"), DEPT_LIONS_COLLEGE)
        
        # Create course objects
        course_start_id = len(courses) + 1
        additional_courses = []
        for idx, course_data in enumerate(additional_course_data):
            course = Course(
                id=course_start_id + idx,
                course_code=course_data["course_code"],
                course_name=course_data["course_name"],
                credits=course_data["credits"],
                course_type=course_data["course_type"],
                department_id=course_data["department_id"],
                course_year=course_data["course_year"],
                semester=course_data["semester"],
            )
            additional_courses.append(course)
        
        db.add_all(additional_courses)
        db.commit()
        print(f"Created {len(additional_courses)} additional courses:")
        print(f"  - Data Intelligence: {sum(1 for c in additional_course_data if c['department_id'] == DEPT_DATA_INTELLIGENCE)}")
        print(f"  - Design Convergence: {sum(1 for c in additional_course_data if c['department_id'] == DEPT_DESIGN_CONVERGENCE)}")
        print(f"  - Architecture: {sum(1 for c in additional_course_data if c['department_id'] == DEPT_ARCHITECTURE)}")
        print(f"  - Entry Requirements (necessary.json): {sum(1 for c in additional_course_data if c['department_id'] == DEPT_LIONS_COLLEGE)}")


        # ====================================================================
        # ADDITIONAL COURSE ENROLLMENTS
        # ====================================================================
        print("Creating additional course enrollments...")
        print(f"Target: ~{TARGET_ADDITIONAL_ENROLLMENTS} enrollments from additional departments")
        
        # Categorize 1st year additional courses by semester
        additional_courses_by_sem = {1: [], 2: []}
        for course_data, course in zip(additional_course_data, additional_courses):
            if course_data["course_year"] == 1:  # Only 1st year courses
                sem = course_data["semester"]
                additional_courses_by_sem[sem].append({
                    "id": course.id,
                    "credits": course_data["credits"],
                    "course_type": course_data["course_type"]
                })

        print(f"  - Additional 1st year, 1st semester: {len(additional_courses_by_sem[1])} courses")
        print(f"  - Additional 1st year, 2nd semester: {len(additional_courses_by_sem[2])} courses")

        # Distribute additional courses to students
        additional_enrollments = []
        enrolled_students = set()
        
        for student_id in student_ids:
            if len(additional_enrollments) >= TARGET_ADDITIONAL_ENROLLMENTS:
                break
            
            # Skip if student already has additional enrollments
            if student_id in enrolled_students:
                continue
            
            # Randomly assign a few additional courses (1-3 courses per semester)
            num_courses_sem1 = random.randint(0, min(3, len(additional_courses_by_sem[1])))
            num_courses_sem2 = random.randint(0, min(3, len(additional_courses_by_sem[2])))
            
            # Select random courses for each semester
            selected_courses_by_sem = {}
            if num_courses_sem1 > 0:
                selected_courses_by_sem[1] = random.sample(additional_courses_by_sem[1], num_courses_sem1)
            if num_courses_sem2 > 0:
                selected_courses_by_sem[2] = random.sample(additional_courses_by_sem[2], num_courses_sem2)
            
            if selected_courses_by_sem:
                student_additional_enrollments = create_course_enrollments(
                    student_id=student_id,
                    courses_by_semester=selected_courses_by_sem,
                    year=2025,
                    max_credits=5,  # Limit additional courses to avoid overloading
                    include_grades=True,
                    shuffle_courses=False  # Already randomly selected
                )
                additional_enrollments.extend(student_additional_enrollments)
                enrolled_students.add(student_id)

        print(f"Adding {len(additional_enrollments)} additional enrollments to database...")
        db.add_all(additional_enrollments)
        db.commit()
        print("Additional course enrollments created successfully!")

        # ====================================================================
        # SURVEY ROUNDS & DECISION STATUSES
        # ====================================================================
        print("Creating survey infrastructure...")
        
        # Survey Rounds
        survey_rounds = [
            SurveyRound(
                id=1, round_number=1, title="2025학년도 1차 전공희망조사",
                status="CLOSED", start_date=datetime(2025, 3, 1), end_date=datetime(2025, 3, 31)
            ),
            SurveyRound(
                id=2, round_number=2, title="2025학년도 2차 전공희망조사",
                status="CLOSED", start_date=datetime(2025, 9, 1), end_date=datetime(2025, 9, 30)
            ),
            SurveyRound(
                id=3, round_number=3, title="2026학년도 3차 전공희망조사",
                status="OPEN", start_date=datetime(2026, 1, 15), end_date=datetime(2026, 2, 15)
            ),
        ]
        db.add_all(survey_rounds)
        
        # Decision Statuses
        decision_statuses = [
            DecisionStatus(id=1, status_name="최종결정"),
            DecisionStatus(id=2, status_name="고민중"),
            DecisionStatus(id=3, status_name="조사중"),
            DecisionStatus(id=4, status_name="미정"),
        ]
        db.add_all(decision_statuses)
        db.commit()

        # ====================================================================
        # MAJOR SURVEYS - Regular Students
        # ====================================================================
        print("Creating major surveys for regular students...")
        surveys = []

        # Popular departments (ordered by popularity for realistic distributions)
        dept_list = [
            300, 500, 205, 305, 206, 306, 600, 207, 601, 303, 304, 200, 700,
            208, 501, 203, 204, 502, 602, 209, 603, 210, 400, 801, 802, 403, 406
        ]

        # Round 1: Focus on popular departments
        print("  - Round 1 surveys...")
        for student_id in student_ids:
            first_choice = random.choice(dept_list[:15])
            second_choice = random.choice([d for d in dept_list if d != first_choice]) if random.random() < 0.7 else None
            
            surveys.append(create_survey_for_student(
                student_id, 1, first_choice, random.randint(1, 5), 2025, 3, second_choice
            ))

        # Round 2: Slightly broadened choices
        print("  - Round 2 surveys...")
        for student_id in student_ids:
            first_choice = random.choice(dept_list[:20])
            second_choice = random.choice([d for d in dept_list if d != first_choice]) if random.random() < 0.6 else None
            
            surveys.append(create_survey_for_student(
                student_id, 2, first_choice, random.randint(2, 5), 2025, 9, second_choice
            ))

        # Round 3: All departments, higher certainty
        print("  - Round 3 surveys...")
        for student_id in student_ids:
            first_choice = random.choice(dept_list)
            second_choice = random.choice([d for d in dept_list if d != first_choice]) if random.random() < 0.5 else None
            
            surveys.append(create_survey_for_student(
                student_id, 3, first_choice, random.randint(3, 5), 2026, 1, second_choice
            ))
        
        # ====================================================================
        # MAJOR SURVEYS - Special Test Students
        # ====================================================================
        print("  - Surveys for special test students (with reproducible patterns)...")
        
        # Create surveys for each special student across all rounds
        # Each student shows realistic progression in their decision-making
        for idx, config in enumerate(SPECIAL_STUDENTS_CONFIG):
            student_id = special_student_ids[idx]
            target_dept = config["target_dept"]
            base_scale = config["decision_scale"]
            
            for round_id, (year, month) in [(1, (2025, 3)), (2, (2025, 9)), (3, (2026, 1))]:
                # Decision certainty evolution based on student profile:
                # - Excellent student: stays confident (5→5→5)
                # - Average student: gradually increases (3→3→4)
                # - Struggling student: remains uncertain (2→2→2)
                if config["grade_profile"] == "excellent":
                    adjusted_scale = 5  # Always confident
                elif config["grade_profile"] == "average":
                    adjusted_scale = min(5, base_scale + (round_id - 1))  # Gradual increase
                else:  # struggling
                    adjusted_scale = base_scale  # Stays uncertain
                
                surveys.append(create_survey_for_student(
                    student_id, round_id, target_dept, adjusted_scale, year, month
                ))

        db.add_all(surveys)
        db.commit()
        print(f"Created {len(surveys)} survey responses")

        # ====================================================================
        # DEPARTMENT ENTRY REQUIREMENTS
        # ====================================================================
        print("Creating sample department entry requirements...")
        
        # Computer Science Department (300) - 2025 admission year
        # Group 1: At least 2 foundational courses with grade B or higher
        req1 = DepartmentEntryRequirement(
            department_id=DEPT_COMPUTER_SCIENCE,
            admission_year=2025,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.B,
            required_count=2,
            requirement_text="다음 전공기초 과목 중 2과목 이상을 B 이상으로 이수해야 합니다.",
            is_alert_required=False
        )
        db.add(req1)
        db.flush()  # Get ID assignment
        
        # Map required courses to this requirement
        cs_basic_courses = ["GEN2052", "GEN1030", "CUL7133"]  # Calculus, Intro to CS, Python & AI
        req_courses = [
            RequirementCourse(requirement_id=req1.id, course_code=code)
            for code in cs_basic_courses
        ]
        db.add_all(req_courses)
        db.commit()
        
        print(f"Created entry requirements for Computer Science department")
        print("Note: StudentRequirementStatus will be populated by evaluation algorithm")

        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "="*70)
        print("[SUCCESS] Database seeded successfully!")
        print("="*70)
        print(f"Created:")
        print(f"  - Students: {len(students)} regular + {len(special_students)} special")
        print(f"  - Courses: {len(courses)} SW + {len(additional_courses)} additional")
        print(f"  - Enrollments: {len(enrollments)} SW + {len(special_enrollments)} special")
        print(f"  - Additional Enrollments: {len(additional_enrollments)}")
        print(f"  - Survey Responses: {len(surveys)}")
        print(f"  - Entry Requirements: 1 sample")
        print(f"\nTotals:")
        print(f"  - Total Students: {len(students) + len(special_students)}")
        print(f"  - Total Courses: {len(courses) + len(additional_courses)}")
        print(f"  - Total Enrollments: {len(enrollments) + len(special_enrollments) + len(additional_enrollments)}")
        print("="*70)

    except Exception as e:
        print(f"[ERROR] Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
