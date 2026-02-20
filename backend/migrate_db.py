"""
데이터베이스 스키마 마이그레이션 스크립트 (updated_database.md 기준)

이 스크립트는 이미 올바른 스키마로 DB가 생성된 후,
추가적인 마이그레이션이 필요할 때 사용합니다.

주요 테이블:
1. colleges - 단과대 테이블
2. departments - 학과 테이블
3. advisors - 지도교수 테이블
4. students - 학생 테이블 (student_id VARCHAR(10) PK)
5. courses - 과목 테이블 (course_id PK)
6. student_courses - 학생 수강과목 테이블
7. survey_rounds - 설문 회차 테이블
8. decision_statuses - 결정 상태 코드 테이블
9. major_surveys - 전공 희망 설문 테이블
10. department_entry_requirements - 학과별 진입 요건
11. requirement_courses - 요건 대상 과목 매핑
12. student_requirement_status - 학생별 진단 결과 캐시
13. curriculums - 교육과정 (유지)
14. course_recommendations - 권장과목 (유지)

초기 설정: docker-compose down -v && docker-compose up --build
"""

import os
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models.models import Base

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/my_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_and_create_tables():
    """모든 테이블이 존재하는지 확인하고, 없으면 생성"""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    expected_tables = {
        'colleges', 'departments', 'advisors', 'students', 'courses',
        'student_courses', 'survey_rounds', 'decision_statuses',
        'major_surveys', 'department_entry_requirements', 'requirement_courses',
        'student_requirement_status', 'curriculums', 'course_recommendations'
    }
    
    missing_tables = expected_tables - existing_tables
    
    if missing_tables:
        logger.info(f"Missing tables: {missing_tables}")
        logger.info("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully!")
    else:
        logger.info("All tables exist. No migration needed.")
    
    return missing_tables


def verify_schema():
    """현재 DB 스키마를 검증"""
    inspector = inspect(engine)
    
    # Check students table has student_id as PK
    columns = {col['name'] for col in inspector.get_columns('students')}
    pk_cols = [col['name'] for col in inspector.get_pk_constraint('students')['constrained_columns']] if 'students' in inspector.get_table_names() else []
    
    if 'student_id' in columns:
        logger.info("✅ students.student_id column exists")
    else:
        logger.warning("❌ students.student_id column missing!")
    
    # Check student_courses table exists (renamed from course_enrollments)
    if 'student_courses' in inspector.get_table_names():
        logger.info("✅ student_courses table exists")
    else:
        logger.warning("❌ student_courses table missing!")
    
    # Check courses table has course_id
    if 'courses' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('courses')}
        if 'course_id' in columns:
            logger.info("✅ courses.course_id column exists")
        if 'course_department' in columns:
            logger.info("✅ courses.course_department column exists")
    
    logger.info("Schema verification complete!")


def run_migration():
    """마이그레이션 실행"""
    logger.info("=" * 60)
    logger.info("Database Migration Script (updated_database.md)")
    logger.info("=" * 60)
    
    missing = check_and_create_tables()
    
    if not missing:
        verify_schema()
    
    logger.info("Migration complete!")


if __name__ == "__main__":
    run_migration()
