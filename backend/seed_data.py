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
        college2 = College(id=2, name="공과대학")
        college3 = College(id=3, name="자연과학대학")
        college4 = College(id=4, name="경영대학")
        college5 = College(id=5, name="인문대학")
        college6 = College(id=6, name="사회과학대학")
        
        db.add_all([college1, college2, college3, college4, college5, college6])
        db.commit()
        
        # Create Departments
        print("Creating departments...")
        departments_list = [
            # 라이언스 칼리지
            Department(id=100, code="LIONSE", name="자율전공학부", college_id=1, min_credits=130),
            
            # 공과대학
            Department(id=201, code="CS", name="컴퓨터공학과", college_id=2, min_credits=130, homepage_url="https://cs.hanyang.ac.kr"),
            Department(id=202, code="EE", name="전자공학과", college_id=2, min_credits=130),
            Department(id=203, code="ME", name="기계공학과", college_id=2, min_credits=135),
            Department(id=204, code="CHEM_ENG", name="화학공학과", college_id=2, min_credits=130),
            Department(id=205, code="CIVIL", name="토목공학과", college_id=2, min_credits=130),
            Department(id=206, code="ARCH", name="건축공학과", college_id=2, min_credits=135),
            Department(id=207, code="IE", name="산업공학과", college_id=2, min_credits=130),
            Department(id=208, code="MATER", name="신소재공학과", college_id=2, min_credits=130),
            
            # 자연과학대학
            Department(id=301, code="MATH", name="수학과", college_id=3, min_credits=126),
            Department(id=302, code="PHYS", name="물리학과", college_id=3, min_credits=126),
            Department(id=303, code="CHEM", name="화학과", college_id=3, min_credits=126),
            Department(id=304, code="BIO", name="생명과학과", college_id=3, min_credits=126),
            Department(id=305, code="EARTH", name="지구환경과학과", college_id=3, min_credits=126),
            Department(id=306, code="ASTRO", name="천문우주학과", college_id=3, min_credits=126),
            
            # 경영대학
            Department(id=401, code="BIZ", name="경영학과", college_id=4, min_credits=126),
            Department(id=402, code="ACCT", name="회계학과", college_id=4, min_credits=126),
            Department(id=403, code="FIN", name="재무금융학과", college_id=4, min_credits=126),
            Department(id=404, code="MKT", name="마케팅학과", college_id=4, min_credits=126),
            
            # 인문대학
            Department(id=501, code="KOR", name="국어국문학과", college_id=5, min_credits=120),
            Department(id=502, code="ENG", name="영어영문학과", college_id=5, min_credits=120),
            Department(id=503, code="HIST", name="사학과", college_id=5, min_credits=120),
            Department(id=504, code="PHIL", name="철학과", college_id=5, min_credits=120),
            Department(id=505, code="CHI", name="중어중문학과", college_id=5, min_credits=120),
            
            # 사회과학대학
            Department(id=601, code="ECON", name="경제학과", college_id=6, min_credits=126),
            Department(id=602, code="POL", name="정치외교학과", college_id=6, min_credits=126),
            Department(id=603, code="SOC", name="사회학과", college_id=6, min_credits=126),
            Department(id=604, code="PSY", name="심리학과", college_id=6, min_credits=126),
            Department(id=605, code="MEDIA", name="미디어커뮤니케이션학과", college_id=6, min_credits=126),
            Department(id=606, code="LAW", name="법학과", college_id=6, min_credits=130),
        ]
        
        db.add_all(departments_list)
        db.commit()
        
        # Create Advisors
        print("Creating advisors...")
        advisors = [
            # 라이언스 칼리지
            Advisor(id=1, name="박교수", email="park@hanyang.ac.kr", department_id=100),
            Advisor(id=2, name="최교수", email="choi@hanyang.ac.kr", department_id=100),
            Advisor(id=3, name="김교수", email="kim@hanyang.ac.kr", department_id=100),
            # 공과대학
            Advisor(id=4, name="이교수", email="lee.cs@hanyang.ac.kr", department_id=201),
            Advisor(id=5, name="정교수", email="jung.ee@hanyang.ac.kr", department_id=202),
            Advisor(id=6, name="강교수", email="kang.me@hanyang.ac.kr", department_id=203),
            # 자연과학대학
            Advisor(id=7, name="송교수", email="song.math@hanyang.ac.kr", department_id=301),
            Advisor(id=8, name="윤교수", email="yoon.phys@hanyang.ac.kr", department_id=302),
            # 경영대학
            Advisor(id=9, name="한교수", email="han.biz@hanyang.ac.kr", department_id=401),
            Advisor(id=10, name="오교수", email="oh.biz@hanyang.ac.kr", department_id=401),
            # 인문대학
            Advisor(id=11, name="서교수", email="seo.kor@hanyang.ac.kr", department_id=501),
            # 사회과학대학
            Advisor(id=12, name="안교수", email="ahn.econ@hanyang.ac.kr", department_id=601),
        ]
        
        db.add_all(advisors)
        db.commit()
        
        # Create Students
        print("Creating students...")
        import random
        random.seed(42)  # 재현 가능한 랜덤 데이터
        
        first_names = ["민준", "서연", "예준", "하은", "지호", "서윤", "주원", "지우", "도윤", "서현",
                      "시우", "수아", "건우", "민서", "현우", "지안", "준서", "채원", "지훈", "유나",
                      "동현", "소율", "승우", "예은", "준혁", "다은", "현준", "시은", "민재", "하린"]
        last_names = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권"]
        
        students = [
            # 라이언스 칼리지 학생들 (자율전공학부)
            Student(
                student_id="202301234", name="홍길동",
                email="hong@hanyang.ac.kr", phone="010-1234-5678",
                department_id=100, advisor_id=1,
                pride="L", class_number=3, status="재학"
            ),
            Student(
                student_id="20210001", name="김민수",
                email="kim.ms@hanyang.ac.kr", phone="010-2001-0001",
                department_id=100, advisor_id=2,
                pride="I", class_number=7, status="재학"
            ),
            Student(
                student_id="20210045", name="이서연",
                email="lee.sy@hanyang.ac.kr", phone="010-2045-0045",
                department_id=100, advisor_id=3,
                pride="O", class_number=2, status="재학"
            ),
            Student(
                student_id="20220012", name="박지훈",
                email="park.jh@hanyang.ac.kr", phone="010-2012-0012",
                department_id=100, advisor_id=1,
                pride="N", class_number=5, status="재학"
            ),
            Student(
                student_id="20220078", name="최예진",
                email="choi.yj@hanyang.ac.kr", phone="010-2078-0078",
                department_id=100, advisor_id=2,
                pride="S", class_number=9, status="휴학"
            ),
        ]
        
        # 다양한 학과에 학생 배치
        prides = ["L", "I", "O", "N", "S", "E"]
        statuses = ["재학"] * 70 + ["휴학"] * 20 + ["졸업"] * 10
        years = [2021, 2022, 2023, 2024]
        
        # 라이언스 칼리지 추가 학생 (약 40명)
        for i in range(6, 46):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}12{i:03d}",
                name=name,
                email=f"lions{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=100,
                advisor_id=random.randint(1, 3),
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 컴퓨터공학과 학생 (약 30명)
        for i in range(100, 130):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}01{i:03d}",
                name=name,
                email=f"cs{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=201,
                advisor_id=4,
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 전자공학과 학생 (약 20명)
        for i in range(200, 220):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}02{i:03d}",
                name=name,
                email=f"ee{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=202,
                advisor_id=5,
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 기계공학과 학생 (약 15명)
        for i in range(300, 315):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}03{i:03d}",
                name=name,
                email=f"me{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=203,
                advisor_id=6,
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 수학과 학생 (약 15명)
        for i in range(400, 415):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}04{i:03d}",
                name=name,
                email=f"math{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=301,
                advisor_id=7,
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 경영학과 학생 (약 25명)
        for i in range(500, 525):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}05{i:03d}",
                name=name,
                email=f"biz{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=401,
                advisor_id=random.choice([9, 10]),
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 영어영문학과 학생 (약 10명)
        for i in range(600, 610):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}06{i:03d}",
                name=name,
                email=f"eng{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=502,
                advisor_id=11,
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        # 경제학과 학생 (약 15명)
        for i in range(700, 715):
            year = random.choice(years)
            name = random.choice(last_names) + random.choice(first_names)
            students.append(Student(
                student_id=f"{year}07{i:03d}",
                name=name,
                email=f"econ{i}@hanyang.ac.kr",
                phone=f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                department_id=601,
                advisor_id=12,
                pride=random.choice(prides),
                class_number=random.randint(1, 10),
                status=random.choice(statuses)
            ))
        
        db.add_all(students)
        db.commit()
        
        # Refresh student objects to get their IDs
        print(f"Refreshing {len(students)} student objects...")
        for student in students:
            db.refresh(student)
        
        # Create Courses
        print("Creating courses...")
        courses = [
            # 컴퓨터공학과 교육과정
            Course(
                id=1, course_code="CS101", course_name="프로그래밍 기초",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="프로그래밍의 기초 개념을 학습합니다. (동등과목: SW101, PROG101)"
            ),
            Course(
                id=2, course_code="SW101", course_name="프로그래밍 기초",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="CS101과 동등과목"
            ),
            Course(
                id=3, course_code="PROG101", course_name="프로그래밍 기초",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="CS101과 동등과목"
            ),
            Course(
                id=4, course_code="MATH101", course_name="미적분학 I",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=5, course_code="MATH102", course_name="미적분학 II",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=6, course_code="CS201", course_name="자료구조",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="동등과목: SW201, DS101"
            ),
            Course(
                id=7, course_code="SW201", course_name="자료구조",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="CS201과 동등과목"
            ),
            Course(
                id=8, course_code="DS101", course_name="자료구조",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="CS201과 동등과목"
            ),
            Course(
                id=9, course_code="MATH201", course_name="선형대수학",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="동등과목: LA101"
            ),
            Course(
                id=10, course_code="LA101", course_name="선형대수학",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="MATH201과 동등과목"
            ),
            Course(
                id=11, course_code="CS202", course_name="알고리즘",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="동등과목: SW301, ALG101"
            ),
            Course(
                id=12, course_code="SW301", course_name="알고리즘",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="CS202와 동등과목"
            ),
            Course(
                id=13, course_code="ALG101", course_name="알고리즘",
                credits=3, course_type="전공진입", department_id=201,
                is_entry_requirement=True, is_recommended=True,
                description="CS202와 동등과목"
            ),
            Course(
                id=14, course_code="STAT201", course_name="확률과 통계",
                credits=3, course_type="권장과목", department_id=201,
                is_entry_requirement=False, is_recommended=True
            ),
            
            # 수학과 교육과정
            Course(
                id=15, course_code="MATH103", course_name="선형대수학 I",
                credits=3, course_type="전공진입", department_id=301,
                is_entry_requirement=True, is_recommended=True,
                description="동등과목: MATH201"
            ),
            Course(
                id=16, course_code="MATH205", course_name="해석학 I",
                credits=3, course_type="전공진입", department_id=301,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=17, course_code="MATH207", course_name="해석학 II",
                credits=3, course_type="전공진입", department_id=301,
                is_entry_requirement=True, is_recommended=True
            ),
            
            # 기타 과목
            Course(
                id=18, course_code="BIZ201", course_name="경영학원론",
                credits=3, course_type="전공필수", department_id=401,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=19, course_code="BIZ202", course_name="회계학",
                credits=3, course_type="전공필수", department_id=401,
                is_entry_requirement=False, is_recommended=True
            ),
            Course(
                id=20, course_code="ME101", course_name="기계공학개론",
                credits=3, course_type="전공기초", department_id=203,
                is_entry_requirement=True, is_recommended=True
            ),
            Course(
                id=21, course_code="GEN001", course_name="글쓰기와 토론",
                credits=2, course_type="교양필수", department_id=100,
                is_entry_requirement=False, is_recommended=False
            ),
        ]
        
        db.add_all(courses)
        db.commit()
        
        # Create Course Enrollments
        print("Creating course enrollments...")
        enrollments = []
        completion_types = ["전공필수", "전공선택", "교양필수", "교양선택", "기초교양"]
        
        # 홍길동(202301234) 수강 과목 - 상세한 이력
        student_hong = next((s for s in students if s.student_id == "202301234"), None)
        if student_hong:
            enrollments.extend([
                CourseEnrollment(
                    student_id=student_hong.id, course_id=2,
                    year=2023, semester=1, completion_type="전공필수", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=4,
                    year=2023, semester=1, completion_type="기초교양", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=21,
                    year=2023, semester=1, completion_type="교양필수", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=7,
                    year=2023, semester=2, completion_type="전공필수", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=5,
                    year=2023, semester=2, completion_type="기초교양", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=12,
                    year=2024, semester=1, completion_type="전공필수", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=10,
                    year=2024, semester=1, completion_type="전공선택", is_retake=False
                ),
                CourseEnrollment(
                    student_id=student_hong.id, course_id=14,
                    year=2024, semester=2, completion_type="전공선택", is_retake=False
                ),
            ])
        
        # 학과별 수강 가능 과목 매핑
        dept_courses_map = {
            100: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 21],  # 라이언스 칼리지
            201: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 21],  # 컴퓨터공학과
            202: [4, 5, 9, 10, 14, 21],  # 전자공학과
            203: [4, 5, 9, 10, 20, 21],  # 기계공학과
            301: [4, 5, 9, 10, 15, 16, 17, 21],  # 수학과
            401: [18, 19, 21],  # 경영학과
            502: [21],  # 영어영문학과
            601: [14, 18, 21],  # 경제학과
        }
        
        # 각 학생에게 현실적인 수강 과목 부여
        print("Generating enrollments for students...")
        for idx, student in enumerate(students):
            if student.student_id == "202301234":  # 홍길동은 이미 처리
                continue
            
            # 학생의 입학년도 파악
            entry_year = int(student.student_id[:4])
            
            # 재학생은 더 많은 과목, 휴학/졸업생은 적거나 과거 데이터만
            if student.status == "휴학":
                num_courses = random.randint(2, 5)
            elif student.status == "졸업":
                num_courses = random.randint(8, 12)
            else:  # 재학
                num_courses = random.randint(3, 8)
            
            # 학과에 따라 수강할 과목 결정
            available_courses = dept_courses_map.get(student.department_id, [21])
            
            # 충분한 과목이 없으면 전체에서 선택
            if len(available_courses) == 0:
                available_courses = [21]
            
            # 랜덤하게 과목 선택 및 수강년도/학기 배정
            selected_courses = random.sample(available_courses, min(num_courses, len(available_courses)))
            
            for i, course_id in enumerate(selected_courses):
                # 입학 후 수강한 년도/학기 계산
                semester_offset = i  # 0부터 시작
                year_offset = semester_offset // 2
                semester = (semester_offset % 2) + 1
                
                current_year = datetime.now().year
                enroll_year = entry_year + year_offset
                if enroll_year > current_year:  # 미래 년도는 현재 연도로 제한
                    enroll_year = current_year
                
                # 졸업생의 경우 과거 데이터
                if student.status == "졸업" and enroll_year >= current_year:
                    # 졸업생은 입학년도부터 현재년도-1 사이에 수강
                    max_year = current_year - 1
                    if max_year >= entry_year:
                        enroll_year = random.randint(entry_year, max_year)
                        semester = random.randint(1, 2)
                    else:
                        enroll_year = entry_year
                        semester = 1
                
                enrollment = CourseEnrollment(
                    student_id=student.id,
                    course_id=course_id,
                    year=enroll_year,
                    semester=semester,
                    completion_type=random.choice(completion_types),
                    is_retake=(random.random() < 0.05)  # 5% 확률로 재수강
                )
                enrollments.append(enrollment)
            
            # 진행 상황 표시 (매 50명마다)
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(students)} students...")
        
        print(f"Adding {len(enrollments)} enrollments to database...")
        db.add_all(enrollments)
        db.commit()
        print("Course enrollments created successfully!")
        
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
        
        dept_survey_data = [
            (201, 58), (202, 38), (401, 35), (304, 25), (203, 22),
            (301, 20), (601, 18), (303, 17), (604, 15), (204, 14),
            (302, 12), (502, 11), (207, 10), (205, 9), (402, 9),
            (206, 8), (403, 8), (602, 7), (208, 7), (603, 6),
            (501, 6), (404, 5), (305, 5), (605, 5), (503, 4),
            (505, 4), (504, 3), (306, 3), (606, 3),
        ]
        
        student_index = 0
        for dept_id, count in dept_survey_data:
            for _ in range(min(count, len(students) - student_index)):
                if student_index >= len(students):
                    break
                student = students[student_index]
                survey = MajorSurvey(
                    student_id=student.id,
                    round_id=1,
                    first_choice_dept_id=dept_id,
                    second_choice_dept_id=dept_survey_data[(student_index + 1) % len(dept_survey_data)][0] if student_index % 2 == 0 else None,
                    decision_scale=(student_index % 5) + 1,
                    submitted_at=datetime(2024, 4, 10) + timedelta(days=student_index % 15)
                )
                surveys.append(survey)
                student_index += 1
        
        for i, student in enumerate(students[:40]):
            dept_idx = (i + 2) % len(dept_survey_data)
            survey = MajorSurvey(
                student_id=student.id,
                round_id=2,
                first_choice_dept_id=dept_survey_data[dept_idx][0],
                second_choice_dept_id=dept_survey_data[(dept_idx + 3) % len(dept_survey_data)][0] if i % 3 != 0 else None,
                decision_scale=(i % 5) + 1,
                submitted_at=datetime(2024, 11, 5) + timedelta(days=i % 20)
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
