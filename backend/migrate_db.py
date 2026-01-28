"""
데이터베이스 스키마 마이그레이션 스크립트

변경사항:
1. Student 테이블에 current_gpa, total_credits 필드 추가
2. DepartmentEntryRequirement 테이블에 logic_operator 필드 추가
3. StudentRequirementStatus 테이블에 세부 평가 점수 필드 추가
"""

from sqlalchemy import text
from database import SessionLocal, engine
from models.database import Base

def migrate_database():
    """데이터베이스 마이그레이션 실행"""
    
    db = SessionLocal()
    
    try:
        print("데이터베이스 마이그레이션 시작...")
        
        # 1. Student 테이블에 GPA 관련 필드 추가
        print("1. Student 테이블 업데이트...")
        # SQLite는 한 번에 하나의 컬럼만 추가 가능
        try:
            db.execute(text("ALTER TABLE students ADD COLUMN current_gpa DECIMAL(3,2) NULL"))
            db.commit()
            print("   ✓ current_gpa 필드 추가 완료")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   - current_gpa 필드가 이미 존재함 (스킵)")
                db.rollback()
            else:
                raise
        
        try:
            db.execute(text("ALTER TABLE students ADD COLUMN total_credits INTEGER DEFAULT 0"))
            db.commit()
            print("   ✓ total_credits 필드 추가 완료")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   - total_credits 필드가 이미 존재함 (스킵)")
                db.rollback()
            else:
                raise
        
        # 2. DepartmentEntryRequirement 테이블에 logic_operator 필드 추가
        print("2. DepartmentEntryRequirement 테이블 업데이트...")
        try:
            db.execute(text("ALTER TABLE department_entry_requirements ADD COLUMN logic_operator VARCHAR(10) DEFAULT 'AND'"))
            db.commit()
            print("   ✓ logic_operator 필드 추가 완료")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   - logic_operator 필드가 이미 존재함 (스킵)")
                db.rollback()
            else:
                raise
        
        # 3. StudentRequirementStatus 테이블에 세부 점수 필드 추가
        print("3. StudentRequirementStatus 테이블 업데이트...")
        score_fields = [
            "gpa_score",
            "required_courses_score",
            "recommended_completion_score",
            "recommended_grade_score",
            "curriculum_completion_score",
            "overall_score"
        ]
        
        for field in score_fields:
            try:
                db.execute(text(f"ALTER TABLE student_requirement_status ADD COLUMN {field} DECIMAL(5,2) NULL"))
                db.commit()
                print(f"   ✓ {field} 필드 추가 완료")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"   - {field} 필드가 이미 존재함 (스킵)")
                    db.rollback()
                else:
                    raise
        
        print("\n마이그레이션 완료!")
        print("\n추가된 필드:")
        print("  - students.current_gpa (학생 평점)")
        print("  - students.total_credits (총 이수 학점)")
        print("  - department_entry_requirements.logic_operator (OR/AND 조건)")
        print("  - student_requirement_status.gpa_score (GPA 점수)")
        print("  - student_requirement_status.required_courses_score (필수과목 점수)")
        print("  - student_requirement_status.recommended_completion_score (권장과목 이수 점수)")
        print("  - student_requirement_status.recommended_grade_score (권장과목 성적 점수)")
        print("  - student_requirement_status.curriculum_completion_score (교육과정 완성도)")
        print("  - student_requirement_status.overall_score (종합 점수)")
        
    except Exception as e:
        print(f"\n마이그레이션 실패: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_database()
