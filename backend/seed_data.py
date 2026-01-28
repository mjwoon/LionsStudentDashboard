"""
Seed script to populate the database with sample data
Run this script to create initial test data
"""

import time
import json
import os
import random
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


# 성적 등급 및 점수 매핑
GRADE_OPTIONS = [
    ('A+', 4.5), ('A0', 4.0), ('A-', 3.7),
    ('B+', 3.3), ('B0', 3.0), ('B-', 2.7),
    ('C+', 2.3), ('C0', 2.0), ('C-', 1.7),
    ('D+', 1.3), ('D0', 1.0), ('D-', 0.7),
    ('F', 0.0)
]

# 성적 가중치 (좋은 성적이 더 많이 나오도록)
GRADE_WEIGHTS = [15, 20, 10, 12, 15, 8, 6, 5, 3, 2, 2, 1, 1]


def generate_random_grade():
    """랜덤 성적 생성 (좋은 성적 편향)"""
    grade, numeric = random.choices(GRADE_OPTIONS, weights=GRADE_WEIGHTS, k=1)[0]
    return grade, numeric


def wait_for_db(max_retries=30, delay=1):
    """Wait for database to be ready"""
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


def seed_database():
    """Populate database with sample data"""

    # Wait for database to be ready
    if not wait_for_db():
        print("Failed to connect to database")
        return

    # Initialize database
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

        # Create Departments
        print("Creating departments...")
        # Load departments from college.json
        college_json_path = os.path.join(os.path.dirname(__file__), "data", "college.json")
        with open(college_json_path, "r", encoding="utf-8") as f:
            college_data = json.load(f)
        
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

        # Create Students
        print("Creating students...")
        import random

        random.seed(42)  # 재현 가능한 랜덤 데이터

        first_names = [
            "민준",
            "서연",
            "예준",
            "하은",
            "지호",
            "서윤",
            "주원",
            "지우",
            "도윤",
            "서현",
            "시우",
            "수아",
            "건우",
            "민서",
            "현우",
            "지안",
            "준서",
            "채원",
            "지훈",
            "유나",
            "동현",
            "소율",
            "승우",
            "예은",
            "준혁",
            "다은",
            "현준",
            "시은",
            "민재",
            "하린",
            "태양",
            "별",
            "하늘",
            "바다",
            "달빛",
            "구름",
            "강물",
            "산들",
            "나무",
            "꽃잎",
        ]
        last_names = [
            "김",
            "이",
            "박",
            "최",
            "정",
            "강",
            "조",
            "윤",
            "장",
            "임",
            "한",
            "오",
            "서",
            "신",
            "권",
            "황",
            "안",
            "송",
            "홍",
            "전",
        ]

        # 계열 분포: 전계열(공대 계열) 40%, 자연계열 30%, 인문사회계열 30%
        tracks = ["전계열"] * 40 + ["자연계열"] * 30 + ["인문사회계열"] * 30
        prides = ["L", "I", "O", "N", "S", "E"]

        students = []

        # 모든 학생을 라이언스 칼리지 2025학번 1학년으로 생성 (200명)
        for i in range(300):
            name = random.choice(last_names) + random.choice(first_names)
            track = random.choice(tracks)
            students.append(
                Student(
                    student_id=f"2025{i:05d}",
                    name=name,
                    email=f"student{i:05d}@hanyang.ac.kr",
                    phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                    department_id=100,  # 라이언스 칼리지
                    advisor_id=random.randint(1, 3),  # 라이언스 칼리지 지도교수
                    track=track,
                    pride=random.choice(prides),
                    class_number=random.randint(1, 10),
                    status="재학",  # 모두 재학생
                )
            )

        db.add_all(students)
        # Extract student IDs before commit (IDs are assigned after add_all but available before commit)
        db.flush()  # This assigns IDs to objects
        student_ids = [student.id for student in students]
        
        # 특별 학생 3명 추가 (mockup data)
        print("Creating 3 special mockup students...")
        special_students = [
            Student(
                student_id="2025123001",
                name="강건",
                email="kang.geon@hanyang.ac.kr",
                phone="010-1111-1111",
                department_id=100,  # 라이언스 칼리지
                advisor_id=random.randint(1, 3),
                track="전계열",
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status="재학",
            ),
            Student(
                student_id="2025123002",
                name="강나라",
                email="kang.nara@hanyang.ac.kr",
                phone="010-2222-2222",
                department_id=100,  # 라이언스 칼리지
                advisor_id=random.randint(1, 3),
                track="자연계열",
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status="재학",
            ),
            Student(
                student_id="2025123003",
                name="강다연",
                email="kang.dayeon@hanyang.ac.kr",
                phone="010-3333-3333",
                department_id=100,  # 라이언스 칼리지
                advisor_id=random.randint(1, 3),
                track="인문사회계열",
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status="재학",
            ),
        ]
        db.add_all(special_students)
        db.flush()
        special_student_ids = [student.id for student in special_students]
        
        db.commit()

        # Create Courses
        print("Creating courses...")

        # Load courses from sw.json
        json_path = os.path.join(os.path.dirname(__file__), "data", "sw.json")
        with open(json_path, "r", encoding="utf-8") as f:
            sw_data = json.load(f)

        courses = []
        for idx, course_data in enumerate(sw_data["curriculum"], start=1):
            course = Course(
                id=idx,
                course_code=course_data["course_code"],
                course_name=course_data["course_name"],
                credits=course_data["credits"],
                course_type=course_data["course_type"],
                department_id=300,  # 컴퓨터학부
                course_year=course_data.get("course_year"),
                semester=course_data.get("semester"),
            )
            courses.append(course)

        db.add_all(courses)
        db.commit()
        print(f"Created {len(courses)} courses from sw.json")

        # Create Course Enrollments
        print("Creating course enrollments...")
        enrollments = []

        # 1학년 과목만 수강 (sw.json에서 course_year=1인 과목들)
        # 1학년 1학기 과목
        first_year_sem1_courses = [
            {"id": idx + 1, "credits": course["credits"], "course_type": course["course_type"]}
            for idx, course in enumerate(sw_data["curriculum"])
            if course["course_year"] == 1 and course["semester"] == 1
        ]
        # 1학년 2학기 과목
        first_year_sem2_courses = [
            {"id": idx + 1, "credits": course["credits"], "course_type": course["course_type"]}
            for idx, course in enumerate(sw_data["curriculum"])
            if course["course_year"] == 1 and course["semester"] == 2
        ]

        print(f"SW 1학년 1학기 과목 수: {len(first_year_sem1_courses)}")
        print(f"SW 1학년 2학기 과목 수: {len(first_year_sem2_courses)}")

        MAX_CREDITS_PER_SEMESTER = 20

        # 각 학생에게 1학년 과목 부여 (학기당 20학점 제한)
        print("Generating SW enrollments for students...")
        for idx, student_id in enumerate(student_ids):
            # 1학기 수강
            sem1_credits = 0
            random.shuffle(first_year_sem1_courses)
            for course_info in first_year_sem1_courses:
                if sem1_credits + course_info["credits"] <= MAX_CREDITS_PER_SEMESTER:
                    grade, numeric_grade = generate_random_grade()
                    enrollment = CourseEnrollment(
                        student_id=student_id,
                        course_id=course_info["id"],
                        year=2025,
                        semester=1,
                        completion_type=course_info["course_type"],
                        is_retake=False,
                        grade=grade,
                        numeric_grade=numeric_grade,
                    )
                    enrollments.append(enrollment)
                    sem1_credits += course_info["credits"]

            # 2학기 수강
            sem2_credits = 0
            random.shuffle(first_year_sem2_courses)
            for course_info in first_year_sem2_courses:
                if sem2_credits + course_info["credits"] <= MAX_CREDITS_PER_SEMESTER:
                    grade, numeric_grade = generate_random_grade()
                    enrollment = CourseEnrollment(
                        student_id=student_id,
                        course_id=course_info["id"],
                        year=2025,
                        semester=2,
                        completion_type=course_info["course_type"],
                        is_retake=False,
                        grade=grade,
                        numeric_grade=numeric_grade,
                    )
                    enrollments.append(enrollment)
                    sem2_credits += course_info["credits"]

            # 진행 상황 표시 (매 50명마다)
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(student_ids)} students...")

        print(f"Adding {len(enrollments)} enrollments to database...")
        db.add_all(enrollments)
        db.commit()
        print("Course enrollments created successfully!")
        
        # 특별 학생 3명에게 동일한 수강 과목 부여
        print("Creating enrollments for 3 special students...")
        special_enrollments = []
        
        # 동일한 과목 리스트 생성 (1학년 1학기, 2학기 각각 18학점 정도)
        # 1학기 수강 과목 고정
        sem1_selected_courses = []
        sem1_total = 0
        for course_info in first_year_sem1_courses[:10]:  # 처음 10개 중에서 선택
            if sem1_total + course_info["credits"] <= 18:
                sem1_selected_courses.append(course_info)
                sem1_total += course_info["credits"]
        
        # 2학기 수강 과목 고정
        sem2_selected_courses = []
        sem2_total = 0
        for course_info in first_year_sem2_courses[:10]:  # 처음 10개 중에서 선택
            if sem2_total + course_info["credits"] <= 18:
                sem2_selected_courses.append(course_info)
                sem2_total += course_info["credits"]
        
        # 3명의 학생에게 동일한 과목, 랜덤 성적 부여
        for student_id in special_student_ids:
            # 1학기 과목
            for course_info in sem1_selected_courses:
                grade, numeric_grade = generate_random_grade()
                enrollment = CourseEnrollment(
                    student_id=student_id,
                    course_id=course_info["id"],
                    year=2025,
                    semester=1,
                    completion_type=course_info["course_type"],
                    is_retake=False,
                    grade=grade,
                    numeric_grade=numeric_grade,
                )
                special_enrollments.append(enrollment)
            
            # 2학기 과목
            for course_info in sem2_selected_courses:
                grade, numeric_grade = generate_random_grade()
                enrollment = CourseEnrollment(
                    student_id=student_id,
                    course_id=course_info["id"],
                    year=2025,
                    semester=2,
                    completion_type=course_info["course_type"],
                    is_retake=False,
                    grade=grade,
                    numeric_grade=numeric_grade,
                )
                special_enrollments.append(enrollment)
        
        print(f"Adding {len(special_enrollments)} special enrollments to database...")
        db.add_all(special_enrollments)
        db.commit()
        print("Special student enrollments created successfully!")

        # Create Data Intelligence Courses from dataIntelli.json
        print("Creating Data Intelligence courses from dataIntelli.json...")
        data_intelli_path = os.path.join(os.path.dirname(__file__), "data", "dataIntelli.json")
        with open(data_intelli_path, "r", encoding="utf-8") as f:
            data_intelli_data = json.load(f)
        
        # Create Design Convergence Courses from designConverge.json
        print("Creating Design Convergence courses from designConverge.json...")
        design_converge_path = os.path.join(os.path.dirname(__file__), "data", "designConverge.json")
        with open(design_converge_path, "r", encoding="utf-8") as f:
            design_converge_data = json.load(f)
        
        # Create Architecture Courses from arch.json
        print("Creating Architecture courses from arch.json...")
        arch_path = os.path.join(os.path.dirname(__file__), "data", "arch.json")
        with open(arch_path, "r", encoding="utf-8") as f:
            arch_data = json.load(f)
        
        # 이미 존재하는 과목 코드 추적 (course_code는 UNIQUE)
        existing_course_codes = {}  # {course_code: (course_name, credits, course_type, department_id)}
        for c in sw_data["curriculum"]:
            existing_course_codes[c["course_code"]] = (c["course_name"], c["credits"], c["course_type"], 300)
        
        # 추가 학과 과목 통합
        additional_courses = []
        additional_course_data = []
        
        # 데이터인텔리전스 과목 추가 (department_id: 303)
        for course_info in data_intelli_data["curriculum"]:
            code = course_info["course_code"]
            # 이미 존재하는 과목이면 스킵 (교양 과목 등)
            if code in existing_course_codes:
                continue
            
            additional_course_data.append({
                "course_code": code,
                "course_name": course_info["course_name"],
                "course_type": course_info["course_type"],
                "credits": course_info["credits"],
                "course_year": course_info["course_year"],
                "semester": course_info["semester"],
                "department_id": 303  # 데이터인텔리전스전공
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], 303)
        
        # 디자인컨버전스 과목 추가 (department_id: 304)
        for course_info in design_converge_data["curriculum"]:
            code = course_info["course_code"]
            # 이미 존재하는 과목이면 스킵
            if code in existing_course_codes:
                continue
                
            additional_course_data.append({
                "course_code": code,
                "course_name": course_info["course_name"],
                "course_type": course_info["course_type"],
                "credits": course_info["credits"],
                "course_year": course_info["course_year"],
                "semester": course_info["semester"],
                "department_id": 304  # 디자인컨버전스전공
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], 304)
        
        # 건축학전공 과목 추가 (department_id: 200)
        for course_info in arch_data["curriculum"]:
            code = course_info["course_code"]
            # 이미 존재하는 과목이면 스킵
            if code in existing_course_codes:
                continue
                
            additional_course_data.append({
                "course_code": code,
                "course_name": course_info["course_name"],
                "course_type": course_info["course_type"],
                "credits": course_info["credits"],
                "course_year": course_info["course_year"],
                "semester": course_info["semester"],
                "department_id": 200  # 건축학전공
            })
            existing_course_codes[code] = (course_info["course_name"], course_info["credits"], course_info["course_type"], 200)
        
        # Create courses (starting from ID after sw.json courses)
        course_start_id = len(courses) + 1
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
        print(f"Created {len(additional_courses)} additional courses")
        print(f"  - Data Intelligence courses: {sum(1 for c in additional_course_data if c['department_id'] == 303)}")
        print(f"  - Design Convergence courses: {sum(1 for c in additional_course_data if c['department_id'] == 304)}")
        print(f"  - Architecture courses: {sum(1 for c in additional_course_data if c['department_id'] == 200)}")

        # 모든 추가 학과 과목 목록 (ICT + 건축학)
        all_additional_courses = additional_courses
        all_additional_course_data = additional_course_data

        # Create Additional Course Enrollments for Data Intelligence and Design Convergence (약 2000개, 1학년 과목만, 학기당 20학점 제한)
        print("Creating additional course enrollments (target: ~2000, 1st year only, max 20 credits/semester)...")
        additional_enrollments = []

        # 과목 ID와 데이터 매핑
        course_id_to_data = {}
        for course_data, course in zip(all_additional_course_data, all_additional_courses):
            course_id_to_data[course.id] = course_data

        # 과목 ID 목록 (1학년만)
        additional_course_ids = [c.id for c in all_additional_courses]

        # 1학년 과목만 학기별로 분류
        additional_courses_by_sem = {1: [], 2: []}
        for course_data, course in zip(all_additional_course_data, all_additional_courses):
            # 1학년 과목만 포함
            if course_data["course_year"] != 1:
                continue
            sem = course_data["semester"]
            additional_courses_by_sem[sem].append({
                "id": course.id,
                "credits": course_data["credits"],
                "course_type": course_data["course_type"]
            })

        print(f"1학년 1학기 과목 수: {len(additional_courses_by_sem[1])}")
        print(f"1학년 2학기 과목 수: {len(additional_courses_by_sem[2])}")

        # 학생별 학기별 학점 추적
        # {student_id: {(year, semester): total_credits}}
        student_semester_credits = {}

        # 기존 SW 수강 기록의 학점 계산
        for e in enrollments:
            key = (e.student_id, e.year, e.semester)
            course_credits = sw_data["curriculum"][e.course_id - 1]["credits"]
            if e.student_id not in student_semester_credits:
                student_semester_credits[e.student_id] = {}
            sem_key = (e.year, e.semester)
            if sem_key not in student_semester_credits[e.student_id]:
                student_semester_credits[e.student_id][sem_key] = 0
            student_semester_credits[e.student_id][sem_key] += course_credits

        MAX_CREDITS_PER_SEMESTER = 20
        target_enrollments = 2000
        enrollment_count = 0

        # 각 학생에게 과목 배정 (학기당 20학점 제한)
        for student_id in student_ids:
            if enrollment_count >= target_enrollments:
                break

            if student_id not in student_semester_credits:
                student_semester_credits[student_id] = {}

            # 1학기와 2학기 모두 수강
            for semester in [1, 2]:
                if enrollment_count >= target_enrollments:
                    break

                year = 2025
                sem_key = (year, semester)

                # 현재 학기 학점 확인
                current_credits = student_semester_credits[student_id].get(sem_key, 0)

                # 해당 학기 과목들을 랜덤하게 섞음
                available = additional_courses_by_sem[semester].copy()
                random.shuffle(available)

                # 이미 수강한 과목 제외를 위한 set
                enrolled_course_ids = set()

                for course_info in available:
                    if enrollment_count >= target_enrollments:
                        break

                    course_id = course_info["id"]
                    credits = course_info["credits"]

                    # 이미 수강한 과목이면 스킵
                    if course_id in enrolled_course_ids:
                        continue

                    # 20학점 초과하면 스킵
                    if current_credits + credits > MAX_CREDITS_PER_SEMESTER:
                        continue

                    # 수강 등록 (2025년 1학기는 진행중이므로 성적 없음)
                    if semester == 1:
                        # 1학기 - 현재 진행중
                        enrollment = CourseEnrollment(
                            student_id=student_id,
                            course_id=course_id,
                            year=year,
                            semester=semester,
                            completion_type=course_info["course_type"],
                            is_retake=random.random() < 0.05,
                            grade=None,
                            numeric_grade=None,
                        )
                    else:
                        # 2학기 - 이미 완료
                        grade, numeric_grade = generate_random_grade()
                        enrollment = CourseEnrollment(
                            student_id=student_id,
                            course_id=course_id,
                            year=year,
                            semester=semester,
                            completion_type=course_info["course_type"],
                            is_retake=random.random() < 0.05,
                            grade=grade,
                            numeric_grade=numeric_grade,
                        )
                    additional_enrollments.append(enrollment)
                    enrolled_course_ids.add(course_id)
                    current_credits += credits
                    enrollment_count += 1

                # 학점 업데이트
                student_semester_credits[student_id][sem_key] = current_credits

        # 목표에 도달하지 못한 경우 추가 생성
        attempts = 0
        max_attempts = 10000
        while enrollment_count < target_enrollments and attempts < max_attempts:
            attempts += 1
            student_id = random.choice(student_ids)
            semester = random.choice([1, 2])
            year = 2025

            if student_id not in student_semester_credits:
                student_semester_credits[student_id] = {}

            sem_key = (year, semester)
            current_credits = student_semester_credits[student_id].get(sem_key, 0)

            # 이미 20학점 이상이면 스킵
            if current_credits >= MAX_CREDITS_PER_SEMESTER:
                continue

            # 해당 학기 과목 중 랜덤 선택
            available = [c for c in additional_courses_by_sem[semester]
                        if current_credits + c["credits"] <= MAX_CREDITS_PER_SEMESTER]

            if not available:
                continue

            course_info = random.choice(available)

            # 2025년 1학기는 진행중이므로 성적 없음
            if semester == 1:
                enrollment = CourseEnrollment(
                    student_id=student_id,
                    course_id=course_info["id"],
                    year=year,
                    semester=semester,
                    completion_type=course_info["course_type"],
                    is_retake=random.random() < 0.05,
                    grade=None,
                    numeric_grade=None,
                )
            else:
                grade, numeric_grade = generate_random_grade()
                enrollment = CourseEnrollment(
                    student_id=student_id,
                    course_id=course_info["id"],
                    year=year,
                    semester=semester,
                    completion_type=course_info["course_type"],
                    is_retake=random.random() < 0.05,
                    grade=grade,
                    numeric_grade=numeric_grade,
                )
            additional_enrollments.append(enrollment)
            student_semester_credits[student_id][sem_key] = current_credits + course_info["credits"]
            enrollment_count += 1

        print(f"Adding {len(additional_enrollments)} additional enrollments to database...")
        db.add_all(additional_enrollments)
        db.commit()
        print("Additional course enrollments created successfully!")

        # Create Survey Rounds (3차까지)
        print("Creating survey rounds...")
        round1 = SurveyRound(
            id=1,
            round_number=1,
            title="2025학년도 1차 전공희망조사",
            status="CLOSED",
            start_date=datetime(2025, 3, 1),
            end_date=datetime(2025, 3, 31),
        )
        round2 = SurveyRound(
            id=2,
            round_number=2,
            title="2025학년도 2차 전공희망조사",
            status="CLOSED",
            start_date=datetime(2025, 9, 1),
            end_date=datetime(2025, 9, 30),
        )
        round3 = SurveyRound(
            id=3,
            round_number=3,
            title="2026학년도 3차 전공희망조사",
            status="OPEN",
            start_date=datetime(2026, 1, 15),
            end_date=datetime(2026, 2, 15),
        )

        db.add_all([round1, round2, round3])
        db.commit()

        # Create Decision Statuses
        print("Creating decision statuses...")
        decision_statuses = [
            DecisionStatus(id=1, status_name="최종결정"),
            DecisionStatus(id=2, status_name="고민중"),
            DecisionStatus(id=3, status_name="조사중"),
            DecisionStatus(id=4, status_name="미정"),
        ]
        db.add_all(decision_statuses)
        db.commit()

        # Create Major Surveys
        print("Creating major surveys...")
        surveys = []

        # 희망 학과 목록 (인기도 순)
        dept_list = [
            300,  # 컴퓨터학부 - 매우 인기
            500,  # 경영학부 - 인기
            205,  # 전자공학부 - 인기
            305,  # 인공지능학과 - 인기
            206,  # 기계공학과
            306,  # 수리데이터사이언스학과
            600,  # 광고홍보학과
            207,  # 배터리소재화학공학과
            601,  # 미디어학과
            303,  # 데이터인텔리전스전공
            304,  # 디자인컨버전스전공
            200,  # 건축학부
            700,  # 글로벌문화통상학부
            208,  # 산업경영공학과
            501,  # 경제학부
            203,  # 건설환경공학과
            204,  # 교통물류공학과
            502,  # 보험계리학과
            602,  # 문화콘텐츠학과
            209,  # 로봇공학과
            603,  # 문화인류학과
            210,  # 에너지바이오학과
            400,  # 차세대반도체융합공학부
            801,  # 융합디자인학부
            802,  # 주얼리패션디자인학과
            403,  # 바이오신약융합학부
            406,  # 국방지능정보융합학부
        ]

        # 1차 조사: 전체 학생 참여 (300명)
        print("  Creating round 1 surveys...")
        for student_id in student_ids:
            first_choice = random.choice(dept_list[:15])  # 인기 학과 위주
            second_choice = None
            if random.random() < 0.7:
                other_depts = [d for d in dept_list if d != first_choice]
                second_choice = random.choice(other_depts)

            survey = MajorSurvey(
                student_id=student_id,
                round_id=1,
                first_choice_dept_id=first_choice,
                second_choice_dept_id=second_choice,
                decision_status_id=random.choice([1, 2, 3, 4]),
                decision_scale=random.randint(1, 5),
                submitted_at=datetime(2025, 3, random.randint(1, 31)),
            )
            surveys.append(survey)

        # 2차 조사: 전체 학생 참여 (300명)
        print("  Creating round 2 surveys...")
        for student_id in student_ids:
            first_choice = random.choice(dept_list[:20])
            second_choice = None
            if random.random() < 0.6:
                other_depts = [d for d in dept_list if d != first_choice]
                second_choice = random.choice(other_depts)

            survey = MajorSurvey(
                student_id=student_id,
                round_id=2,
                first_choice_dept_id=first_choice,
                second_choice_dept_id=second_choice,
                decision_status_id=random.choice([1, 2, 3, 4]),
                decision_scale=random.randint(2, 5),
                submitted_at=datetime(2025, 9, random.randint(1, 30)),
            )
            surveys.append(survey)

        # 3차 조사: 전체 학생 참여 (300명)
        print("  Creating round 3 surveys...")
        for student_id in student_ids:
            first_choice = random.choice(dept_list)
            second_choice = None
            if random.random() < 0.5:
                other_depts = [d for d in dept_list if d != first_choice]
                second_choice = random.choice(other_depts)

            survey = MajorSurvey(
                student_id=student_id,
                round_id=3,
                first_choice_dept_id=first_choice,
                second_choice_dept_id=second_choice,
                decision_status_id=random.choice([1, 2, 3, 4]),
                decision_scale=random.randint(3, 5),
                submitted_at=datetime(2026, 1, random.randint(15, 27)),
            )
            surveys.append(survey)
        
        # 특별 학생 3명의 설문 조사 (모든 라운드에 참여)
        print("  Creating surveys for 3 special students...")
        # 학과 ID 확인: 데이터인텔리전스전공=303, 디자인컨버전스전공=304
        
        special_survey_data = [
            # 강건: 데이터인텔리전스전공, 보통(3)
            {
                "student_id": special_student_ids[0],
                "first_choice": 303,  # 데이터인텔리전스전공
                "decision_scale": 3,  # 보통
            },
            # 강나라: 데이터인텔리전스전공, 매우 확실(5)
            {
                "student_id": special_student_ids[1],
                "first_choice": 303,  # 데이터인텔리전스전공
                "decision_scale": 5,  # 매우 확실
            },
            # 강다연: 디자인컨버전스전공, 불확실(2)
            {
                "student_id": special_student_ids[2],
                "first_choice": 304,  # 디자인컨버전스전공
                "decision_scale": 2,  # 불확실
            },
        ]
        
        # 각 라운드별로 특별 학생 설문 추가
        for round_id, round_month in [(1, 3), (2, 9), (3, 1)]:
            for idx, data in enumerate(special_survey_data):
                # 2차, 3차로 갈수록 결정도가 높아지도록 조정
                adjusted_scale = min(5, data["decision_scale"] + (round_id - 1))
                
                survey = MajorSurvey(
                    student_id=data["student_id"],
                    round_id=round_id,
                    first_choice_dept_id=data["first_choice"],
                    second_choice_dept_id=None,  # 2지망 없음
                    decision_status_id=1 if adjusted_scale >= 4 else 2,  # 확실하면 최종결정, 아니면 고민중
                    decision_scale=adjusted_scale,
                    submitted_at=datetime(
                        2025 if round_id < 3 else 2026,
                        round_month,
                        random.randint(1, 28)
                    ),
                )
                surveys.append(survey)

        db.add_all(surveys)
        db.commit()

        # Create Sample Department Entry Requirements (샘플 데이터)
        print("Creating sample department entry requirements...")
        sample_requirements = []
        
        # 컴퓨터학부 (300) 진입요건 - 2025학번용
        # 그룹1: 전공기초 과목 중 2과목 이상 B 이상
        req1 = DepartmentEntryRequirement(
            department_id=300,
            admission_year=2025,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.B,
            required_count=2,
            requirement_text="다음 전공기초 과목 중 2과목 이상을 B 이상으로 이수해야 합니다.",
            is_alert_required=False
        )
        sample_requirements.append(req1)
        
        db.add_all(sample_requirements)
        db.flush()  # ID 할당
        
        # 요건 과목 매핑 (컴퓨터학부 그룹1)
        # 실제 존재하는 전공기초/전공핵심 과목 코드 사용
        req_courses = []
        cs_basic_courses = ["GEN2052", "GEN1030", "CUL7133"]  # 미분적분학1, 컴퓨터개론, 파이썬과인공지능
        for code in cs_basic_courses:
            req_courses.append(RequirementCourse(
                requirement_id=req1.id,
                course_code=code
            ))
        
        db.add_all(req_courses)
        db.commit()
        print(f"Created {len(sample_requirements)} sample entry requirements")
        print("Note: StudentRequirementStatus table is empty - will be populated by evaluation algorithm")

        print("[SUCCESS] Database seeded successfully!")
        print(f"Created:")
        print(f"  - {len(students)} students")
        print(f"  - {len(courses)} SW courses")
        print(f"  - {len(all_additional_courses)} additional courses (Data Intelligence + Design Convergence + Architecture)")
        print(f"  - {len(enrollments)} SW course enrollments")
        print(f"  - {len(additional_enrollments)} additional enrollments")
        print(f"  - {len(surveys)} survey submissions")
        print(f"  - Total courses: {len(courses) + len(all_additional_courses)}")
        print(f"  - Total enrollments: {len(enrollments) + len(additional_enrollments)}")

    except Exception as e:
        print(f"[ERROR] Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
