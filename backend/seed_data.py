"""
Seed script to populate the database with sample data
Run this script to create initial test data
"""
import time
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from database import SessionLocal, init_db
from models.database import (
    College, Department, Advisor, Student, Course, 
    CourseEnrollment, SurveyRound, MajorSurvey
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
        # Clear existing data (optional - comment out if you want to keep existing data)
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
        college2 = College(id=2, name="공과대학")
        college3 = College(id=3, name="경영대학")
        college4 = College(id=4, name="자연과학대학")
        
        db.add_all([college1, college2, college3, college4])
        db.commit()
        
        # Create Departments
        print("Creating departments...")
        dept1 = Department(
            id=100, code="LIONSE", name="자율전공학부", 
            college_id=1, min_credits=130
        )
        dept2 = Department(
            id=201, code="CSE", name="컴퓨터공학과", 
            college_id=2, min_credits=130,
            homepage_url="https://cs.hanyang.ac.kr"
        )
        dept3 = Department(
            id=205, code="BIZ", name="경영학과", 
            college_id=3, min_credits=126
        )
        dept4 = Department(
            id=208, code="ME", name="기계공학과", 
            college_id=2, min_credits=135
        )
        dept5 = Department(
            id=210, code="EE", name="전자공학과", 
            college_id=2, min_credits=130
        )
        
        db.add_all([dept1, dept2, dept3, dept4, dept5])
        db.commit()
        
        # Create Advisors
        print("Creating advisors...")
        advisor1 = Advisor(id=1, name="박교수", email="park@hanyang.ac.kr", department_id=100)
        advisor2 = Advisor(id=2, name="최교수", email="choi@hanyang.ac.kr", department_id=100)
        advisor3 = Advisor(id=3, name="김교수", email="kim@hanyang.ac.kr", department_id=100)
        
        db.add_all([advisor1, advisor2, advisor3])
        db.commit()
        
        # Create Students
        print("Creating students...")
        students = []
        prides = ["L", "I", "O", "N", "S", "E"]
        for i in range(1, 51):
            student = Student(
                student_id=f"202412{i:03d}",
                name=f"학생{i}",
                email=f"student{i}@hanyang.ac.kr",
                phone=f"010-{1000+i:04d}-{5678}",
                department_id=100,
                advisor_id=(i % 3) + 1,
                pride=prides[i % 6],
                class_number=(i % 2) + 1,
                status="재학"
            )
            students.append(student)
        
        db.add_all(students)
        db.commit()
        
        # Create Courses
        print("Creating courses...")
        courses = [
            Course(
                id=1, course_code="CSE101", course_name="프로그래밍 기초",
                credits=3, course_type="전공기초", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="프로그래밍의 기초 개념을 학습합니다."
            ),
            Course(
                id=2, course_code="CSE102", course_name="데이터구조",
                credits=3, course_type="전공핵심", department_id=201,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=3, course_code="MATH101", course_name="미적분학 1",
                credits=3, course_type="기초과학", department_id=201,
                is_entry_requirement=True, is_recommended=False
            ),
            Course(
                id=4, course_code="MGT201", course_name="경영학원론",
                credits=3, course_type="전공필수", department_id=205,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=5, course_code="MGT202", course_name="회계학",
                credits=3, course_type="전공필수", department_id=205,
                is_entry_requirement=False, is_recommended=True
            ),
            Course(
                id=6, course_code="ME101", course_name="기계공학개론",
                credits=3, course_type="전공기초", department_id=208,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=7, course_code="GEN001", course_name="글쓰기와 토론",
                credits=2, course_type="교양필수", department_id=100,
                is_entry_requirement=False, is_recommended=False
            ),
        ]
        
        db.add_all(courses)
        db.commit()
        
        # Create Course Enrollments
        print("Creating course enrollments...")
        enrollments = []
        for student in students[:30]:  # First 30 students
            # Each student takes 2-3 courses
            enrollment1 = CourseEnrollment(
                student_id=student.id,
                course_id=1,
                year=2024,
                semester=1,
                completion_type="전공기초",
                is_retake=False
            )
            enrollment2 = CourseEnrollment(
                student_id=student.id,
                course_id=7,
                year=2024,
                semester=1,
                completion_type="교양필수",
                is_retake=False
            )
            enrollments.extend([enrollment1, enrollment2])
            
            # Some students take additional courses
            if student.id % 3 == 0:
                enrollment3 = CourseEnrollment(
                    student_id=student.id,
                    course_id=2,
                    year=2024,
                    semester=1,
                    completion_type="전공핵심",
                    is_retake=False
                )
                enrollments.append(enrollment3)
        
        db.add_all(enrollments)
        db.commit()
        
        # Create Survey Rounds
        print("Creating survey rounds...")
        round1 = SurveyRound(
            id=1,
            round_number=1,
            title="2024학년도 1차 전공희망조사",
            status="CLOSED",
            start_date=datetime(2024, 4, 1),
            end_date=datetime(2024, 4, 15)
        )
        round2 = SurveyRound(
            id=2,
            round_number=2,
            title="2024학년도 2차 전공희망조사",
            status="OPEN",
            start_date=datetime(2024, 11, 1),
            end_date=datetime(2024, 11, 30)
        )
        
        db.add_all([round1, round2])
        db.commit()
        
        # Create Major Surveys
        print("Creating major surveys...")
        surveys = []
        dept_choices = [201, 205, 208, 210]
        
        # First round surveys (for first 40 students)
        for student in students[:40]:
            survey = MajorSurvey(
                student_id=student.id,
                round_id=1,
                first_choice_dept_id=dept_choices[student.id % 4],
                second_choice_dept_id=dept_choices[(student.id + 1) % 4],
                decision_scale=(student.id % 5) + 1,
                submitted_at=datetime(2024, 4, 10) + timedelta(days=student.id % 5)
            )
            surveys.append(survey)
        
        # Second round surveys (for first 35 students)
        for student in students[:35]:
            survey = MajorSurvey(
                student_id=student.id,
                round_id=2,
                first_choice_dept_id=dept_choices[student.id % 4],
                second_choice_dept_id=dept_choices[(student.id + 2) % 4] if student.id % 3 != 0 else None,
                decision_scale=(student.id % 5) + 1,
                submitted_at=datetime(2024, 11, 5) + timedelta(days=student.id % 10)
            )
            surveys.append(survey)
        
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
