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

import random
from database import SessionLocal, init_db
from models.models import (
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

# Import configuration and services
from fixtures.seed_config import (
    DEPT_LIONS_COLLEGE,
    DEPT_COMPUTER_SCIENCE,
    DEPT_DATA_INTELLIGENCE,
    DEPT_DESIGN_CONVERGENCE,
    DEPT_ARCHITECTURE,
    DEPT_ELECTRONICS,
    DEPT_INDUSTRIAL_ENG,
    DEPT_INDUSTRIAL_MGMT,
    DEPT_MOLECULAR_PHARM,
    DEPT_ADVERTISING_PR,
    REGULAR_STUDENT_COUNT,
    SPECIAL_STUDENTS_CONFIG,
    ADVISORS_DATA,
    COLLEGES_DATA,
    MAX_CREDITS_PER_SEMESTER,
    TARGET_ADDITIONAL_ENROLLMENTS,
)
from services.seed_service import (
    wait_for_db,
    load_json_data,
    create_course_enrollments,
    create_survey_for_student,
    update_student_gpa,
    generate_random_grade,
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
    if not wait_for_db(SessionLocal):
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
        colleges = [College(id=c["id"], name=c["name"]) for c in COLLEGES_DATA]
        db.add_all(colleges)
        db.commit()
        print(f"Created {len(colleges)} colleges")

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
        advisors = [Advisor(**advisor_data) for advisor_data in ADVISORS_DATA]
        db.add_all(advisors)
        db.commit()
        print(f"Created {len(advisors)} advisors")

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
        # ADDITIONAL COURSES (Data Intelligence, Design Convergence, Architecture, Electronics)
        # ====================================================================
        print("Loading additional department courses...")
        data_intelli_data = load_json_data("dataIntelli.json")
        design_converge_data = load_json_data("designConverge.json")
        arch_data = load_json_data("arch.json")
        elec_data = load_json_data("elec.json")
        ime_data = load_json_data("ime.json")
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
        
        # Add Electronics courses (dept_id: 204)
        for course_info in elec_data["curriculum"]:
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
                "department_id": DEPT_ELECTRONICS
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], DEPT_ELECTRONICS)
        
        # Add Industrial Management Engineering courses (dept_id: 207)
        for course_info in ime_data["curriculum"]:
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
                "department_id": DEPT_INDUSTRIAL_MGMT
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], DEPT_INDUSTRIAL_MGMT)
        
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
        print(f"  - Electronics: {sum(1 for c in additional_course_data if c['department_id'] == DEPT_ELECTRONICS)}")
        print(f"  - Industrial Management Engineering: {sum(1 for c in additional_course_data if c['department_id'] == DEPT_INDUSTRIAL_MGMT)}")
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
        # DEPARTMENT ENTRY REQUIREMENTS (2026년도)
        # ====================================================================
        print("Creating department entry requirements for 2026...")
        
        # 1. 전자공학부 (204) - OR 조건: 5개 과목 중 B 이상 2과목 OR A 이상 1과목
        req_elec_or = DepartmentEntryRequirement(
            department_id=DEPT_ELECTRONICS,
            admission_year=2026,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.A,  # OR 조건의 첫 번째 (A 이상 1과목)
            required_count=1,
            logic_operator="OR",
            requirement_text="아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수",
            is_alert_required=True
        )
        db.add(req_elec_or)
        db.flush()
        
        # OR 조건 - Group 2: B 이상 2과목
        req_elec_and = DepartmentEntryRequirement(
            department_id=DEPT_ELECTRONICS,
            admission_year=2026,
            requirement_group=2,
            target_grade_level=GradeLevelEnum.B,
            required_count=2,
            logic_operator="AND",
            requirement_text="아래 5개 과목 중 성적 B(3.0) 이상 2과목 필수",
            is_alert_required=True
        )
        db.add(req_elec_and)
        db.flush()
        
        elec_courses = ["ELE3037", "GEN2052", "GEN0063", "GEN2053", "GEN0064"]  # 확률과통계, 미분적분학1, 일반물리학1, 미분적분학2, 일반물리학2
        for course_code in elec_courses:
            db.add(RequirementCourse(requirement_id=req_elec_or.id, course_code=course_code))
            db.add(RequirementCourse(requirement_id=req_elec_and.id, course_code=course_code))
        
        print(f"  ✓ 전자공학부: OR 조건 (A 1과목 OR B 2과목)")
        
        # 2. 산업경영공학과 (207) - C 이상 1과목
        req_ie = DepartmentEntryRequirement(
            department_id=DEPT_INDUSTRIAL_ENG,
            admission_year=2026,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.C,
            required_count=1,
            logic_operator="AND",
            requirement_text="미분적분학1 C(2.0) 이상 필수",
            is_alert_required=True
        )
        db.add(req_ie)
        db.flush()
        
        db.add(RequirementCourse(requirement_id=req_ie.id, course_code="GEN2052"))  # 미분적분학1
        print(f"  ✓ 산업경영공학과: C 이상 1과목")
        
        # 3. 분자의약전공 (404) - B 이상 1과목
        req_pharm = DepartmentEntryRequirement(
            department_id=DEPT_MOLECULAR_PHARM,
            admission_year=2026,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.B,
            required_count=1,
            logic_operator="AND",
            requirement_text="아래 2개 과목 중 B(3.0) 이상 1과목 필수",
            is_alert_required=True
        )
        db.add(req_pharm)
        db.flush()
        
        pharm_courses = ["GEN0074", "GEN0075"]  # 일반생물학1, 일반생물학2
        for course_code in pharm_courses:
            db.add(RequirementCourse(requirement_id=req_pharm.id, course_code=course_code))
        
        print(f"  ✓ 분자의약전공: B 이상 1과목 (2개 중)")
        
        # 4. 광고홍보학과 (603) - B 이상 1과목
        # Note: 광고홍보학과의 정확한 department_id는 college.json 확인 필요
        # 여기서는 603으로 가정 (커뮤니케이션&컬쳐대학)
        try:
            req_adpr = DepartmentEntryRequirement(
                department_id=DEPT_ADVERTISING_PR,
                admission_year=2026,
                requirement_group=1,
                target_grade_level=GradeLevelEnum.B,
                required_count=1,
                logic_operator="AND",
                requirement_text="아래 5개 과목 중 B(3.0) 이상 1과목 필수",
                is_alert_required=True
            )
            db.add(req_adpr)
            db.flush()
            
            adpr_courses = ["APR1004", "APR2013", "APR2014", "APR1038", "APR1037"]  # 커뮤니케이션론, 광고원론, 홍보원론, 크리에이티브디자인, 전략적커뮤니케이션
            for course_code in adpr_courses:
                db.add(RequirementCourse(requirement_id=req_adpr.id, course_code=course_code))
            
            print(f"  ✓ 광고홍보학과: B 이상 1과목 (5개 중)")
        except Exception as e:
            print(f"  ⚠ 광고홍보학과 진입요건 생성 실패: {e}")
        
        db.commit()
        print(f"Created entry requirements for 4 departments (2026 admission year)")
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
