import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Base, College, Department, Curriculum, Course, CourseRecommendation, DepartmentEntryRequirement

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/my_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_test_curriculum():
    db = SessionLocal()
    
    # Check if we already seeded a department from earlier test
    dept = db.query(Department).filter(Department.code == "CS").first()
    if not dept:
        print("No CS department found. Run seed_departments.py first.")
        return

    print(f"Department found: {dept.name} (ID: {dept.id})")
    
    # Seed some test courses
    test_courses = [
        Course(course_code="CSE1101", course_name="프로그래밍기초", credits=3,
               course_type="전공기초", course_department=dept.id, course_year=1, semester=1),
        Course(course_code="CSE1102", course_name="자료구조", credits=3,
               course_type="전공필수", course_department=dept.id, course_year=1, semester=2),
        Course(course_code="CSE2101", course_name="알고리즘", credits=3,
               course_type="전공필수", course_department=dept.id, course_year=2, semester=1),
    ]
    
    for course in test_courses:
        existing = db.query(Course).filter(Course.course_code == course.course_code).first()
        if not existing:
            db.add(course)
            print(f"  Added course: {course.course_name}")
    
    db.commit()
    
    # Seed curriculum entries
    test_curriculums = [
        Curriculum(department_id=dept.id, course_year=1, course_code="CSE1101", course_name="프로그래밍기초"),
        Curriculum(department_id=dept.id, course_year=1, course_code="CSE1102", course_name="자료구조"),
        Curriculum(department_id=dept.id, course_year=2, course_code="CSE2101", course_name="알고리즘"),
    ]
    
    for cur in test_curriculums:
        existing = db.query(Curriculum).filter(
            Curriculum.department_id == cur.department_id,
            Curriculum.course_code == cur.course_code
        ).first()
        if not existing:
            db.add(cur)
            print(f"  Added curriculum: {cur.course_name}")
    
    db.commit()
    print("Test curriculum seeded successfully!")
    db.close()

if __name__ == "__main__":
    seed_test_curriculum()
