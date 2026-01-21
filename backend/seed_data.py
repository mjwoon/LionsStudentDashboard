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
)
from datetime import datetime, timedelta


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
        db.query(MajorSurvey).delete()
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
                id=8, name="윤교수", email="yoon.math@hanyang.ac.kr", department_id=307
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
        for i in range(200):
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
        db.commit()

        # Create Courses
        print("Creating courses...")

        # Load courses from sw.json
        json_path = os.path.join(os.path.dirname(__file__), "data", "sw.json")
        with open(json_path, "r", encoding="utf-8") as f:
            sw_data = json.load(f)

        courses = []
        for idx, course_data in enumerate(sw_data["curriculum"], start=1):
            # Determine if course is entry requirement based on course_type
            is_entry_req = course_data["course_type"] in ["전공기초", "전공핵심"]
            is_recommended = course_data["course_type"] in [
                "전공기초",
                "전공핵심",
                "교양필수",
            ]

            course = Course(
                id=idx,
                course_code=course_data["course_code"],
                course_name=course_data["course_name"],
                credits=course_data["credits"],
                course_type=course_data["course_type"],
                department_id=300,  # 컴퓨터학부
                course_year=course_data.get("course_year"),
                semester=course_data.get("semester"),
                is_entry_requirement=is_entry_req,
                is_recommended=is_recommended,
            )
            courses.append(course)

        db.add_all(courses)
        db.commit()
        print(f"Created {len(courses)} courses from sw.json")

        # Create Course Enrollments
        print("Creating course enrollments...")
        enrollments = []

        # 1학년이므로 1학년 1학기 과목만 수강 (sw.json에서 course_year=1, semester=1인 과목들)
        # sw.json에서 1학년 1학기 과목들의 ID 찾기
        first_year_first_sem_courses = [
            idx + 1
            for idx, course in enumerate(sw_data["curriculum"])
            if course["course_year"] == 1 and course["semester"] == 1
        ]

        print(f"1학년 1학기 과목 수: {len(first_year_first_sem_courses)}")

        # 각 학생에게 현실적인 1학년 1학기 수강 과목 부여
        print("Generating enrollments for students...")
        for idx, student_id in enumerate(student_ids):
            # 1학년 1학기는 3-5과목 정도 수강
            num_courses = min(random.randint(3, 5), len(first_year_first_sem_courses))

            # 랜덤하게 과목 선택
            selected_courses = random.sample(first_year_first_sem_courses, num_courses)

            for course_id in selected_courses:
                enrollment = CourseEnrollment(
                    student_id=student_id,
                    course_id=course_id,
                    year=2025,
                    semester=1,
                    completion_type=sw_data["curriculum"][course_id - 1]["course_type"],
                    is_retake=False,
                )
                enrollments.append(enrollment)

            # 진행 상황 표시 (매 50명마다)
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(student_ids)} students...")

        print(f"Adding {len(enrollments)} enrollments to database...")
        db.add_all(enrollments)
        db.commit()
        print("Course enrollments created successfully!")

        # Create Survey Rounds
        print("Creating survey rounds...")
        round1 = SurveyRound(
            id=1,
            round_number=1,
            title="2025학년도 1차 전공희망조사",
            status="CLOSED",
            start_date=datetime(2025, 9, 1),
            end_date=datetime(2025, 9, 30),
        )
        round2 = SurveyRound(
            id=2,
            round_number=2,
            title="2026학년도 2차 전공희망조사",
            status="OPEN",
            start_date=datetime(2026, 1, 15),
            end_date=datetime(2026, 2, 15),
        )

        db.add_all([round1, round2])
        db.commit()

        # Create Major Surveys
        print("Creating major surveys...")
        surveys = []

        # 전공별 희망 학생 수 (더 다양하고 현실적으로)
        # 인기학과: 컴공, 경영, 전자공학, AI
        # 중간: 기계, ICT, 건축 등
        # 비인기: 배터리, 디자인 등
        dept_preferences = [
            # (학과ID, 1차조사 희망자수, 2차조사 희망자수)
            (300, 35, 28),  # 컴퓨터학부 - 매우 인기
            (500, 28, 25),  # 경영학부 - 인기
            (205, 22, 18),  # 전자공학부 - 인기
            (306, 18, 15),  # 인공지능학과 - 인기
            (206, 15, 12),  # 기계공학과
            (307, 14, 11),  # 수리데이터사이언스학과
            (600, 12, 10),  # 광고홍보학과
            (207, 10, 9),  # 배터리소재화학공학과
            (601, 9, 8),  # 미디어학과
            (303, 8, 7),  # ICT융합학부
            (200, 7, 6),  # 건축학부
            (700, 7, 6),  # 글로벌문화통상학부
            (208, 6, 5),  # 산업경영공학과
            (501, 6, 5),  # 경제학부
            (203, 5, 4),  # 건설환경공학과
            (204, 5, 5),  # 교통물류공학과
            (502, 5, 4),  # 보험계리학과
            (602, 4, 4),  # 문화콘텐츠학과
            (209, 4, 3),  # 로봇공학과
            (603, 4, 3),  # 문화인류학과
            (210, 3, 3),  # 에너지바이오학과
            (211, 3, 3),  # 해양융합공학과
            (400, 3, 2),  # 차세대반도체융합공학부
            (801, 3, 3),  # 융합디자인학부
            (802, 2, 2),  # 주얼리패션디자인학과 (실제로는 800)
            (403, 2, 2),  # 바이오신양융합학부
            (406, 2, 1),  # 국방지능정보융합학부
        ]

        # 1차 조사 생성 (총 200명 중 약 90% 참여)
        student_index = 0
        for dept_id, count_r1, _ in dept_preferences:
            for _ in range(count_r1):
                if student_index >= len(student_ids):
                    break
                student_id = student_ids[student_index]

                # 2지망은 60% 확률로 작성
                second_choice = None
                if random.random() < 0.6:
                    # 다른 학과를 2지망으로 랜덤 선택
                    other_depts = [d[0] for d in dept_preferences if d[0] != dept_id]
                    second_choice = random.choice(other_depts)

                survey = MajorSurvey(
                    student_id=student_id,
                    round_id=1,
                    first_choice_dept_id=dept_id,
                    second_choice_dept_id=second_choice,
                    decision_scale=random.randint(1, 5),  # 1~5점 랜덤
                    submitted_at=datetime(2025, 9, random.randint(1, 30)),
                )
                surveys.append(survey)
                student_index += 1

        # 2차 조사 생성 (1차 미참여자 + 마음이 바뀐 학생들)
        student_index2 = 0
        for dept_id, _, count_r2 in dept_preferences:
            for _ in range(count_r2):
                if student_index2 >= len(student_ids):
                    break
                student_id = student_ids[student_index2]

                # 2지망은 50% 확률로 작성
                second_choice = None
                if random.random() < 0.5:
                    other_depts = [d[0] for d in dept_preferences if d[0] != dept_id]
                    second_choice = random.choice(other_depts)

                survey = MajorSurvey(
                    student_id=student_id,
                    round_id=2,
                    first_choice_dept_id=dept_id,
                    second_choice_dept_id=second_choice,
                    decision_scale=random.randint(2, 5),  # 2차는 2~5점 (조금 더 확신)
                    submitted_at=(
                        datetime(2026, 1, random.randint(15, 31))
                        if random.randint(15, 31) <= 31
                        else datetime(2026, 2, random.randint(1, 15))
                    ),
                )
                surveys.append(survey)
                student_index2 += 1

        db.add_all(surveys)
        db.commit()

        print("✅ Database seeded successfully!")
        print(f"Created:")
        print(f"  - {len(students)} students")
        print(f"  - {len(courses)} courses")
        print(f"  - {len(enrollments)} course enrollments")
        print(f"  - {len(surveys)} survey submissions")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
