"""
데이터베이스 스키마 마이그레이션 스크립트 (통합본)

최종 목표: 2-메트릭 평가 시스템
- curriculum_completion_score: 1학년 전공체계도 완성도 (70%)
- related_courses_score: 유사과목 점수 (30%)

마이그레이션 단계:
1. Student 테이블에 current_gpa, total_credits 필드 추가
2. DepartmentEntryRequirement 테이블에 logic_operator 필드 추가
3. StudentRequirementStatus 테이블에 2-메트릭 평가 필드 추가/정리
   - 기존 5-메트릭 컬럼 삭제 (있다면)
   - 최종 2-메트릭 컬럼만 유지
"""

from sqlalchemy import text
from database import SessionLocal, engine
from models.models import Base

def migrate_database():
    """데이터베이스 마이그레이션 실행"""
    
    db = SessionLocal()
    
    try:
        print("="*80)
        print("데이터베이스 마이그레이션 시작 (2-메트릭 평가 시스템)")
        print("="*80)
        
        # 1. Student 테이블에 GPA 관련 필드 추가
        print("\n[1/4] Student 테이블 업데이트...")
        student_fields = [
            ("current_gpa", "DECIMAL(3,2)", "학생 평점"),
            ("total_credits", "INTEGER DEFAULT 0", "총 이수 학점")
        ]
        
        for field_name, field_type, description in student_fields:
            try:
                db.execute(text(f"ALTER TABLE students ADD COLUMN {field_name} {field_type}"))
                db.commit()
                print(f"   ✓ {field_name} 필드 추가 완료 ({description})")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"   - {field_name} 필드가 이미 존재함 (스킵)")
                    db.rollback()
                else:
                    raise
        
        # 2. DepartmentEntryRequirement 테이블에 logic_operator 필드 추가
        print("\n[2/4] DepartmentEntryRequirement 테이블 업데이트...")
        try:
            db.execute(text("ALTER TABLE department_entry_requirements ADD COLUMN logic_operator VARCHAR(10) DEFAULT 'AND'"))
            db.commit()
            print("   ✓ logic_operator 필드 추가 완료 (OR/AND 조건)")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   - logic_operator 필드가 이미 존재함 (스킵)")
                db.rollback()
            else:
                raise
        
        # 3. StudentRequirementStatus - 구 5-메트릭 컬럼 삭제
        print("\n[3/4] StudentRequirementStatus 테이블 - 구 메트릭 정리...")
        old_columns = [
            "gpa_score",
            "required_courses_score",
            "recommended_completion_score",
            "recommended_grade_score"
        ]
        
        for column in old_columns:
            try:
                db.execute(text(f"ALTER TABLE student_requirement_status DROP COLUMN IF EXISTS {column}"))
                db.commit()
                print(f"   ✓ {column} 삭제됨")
            except Exception as e:
                if "no such column" in str(e).lower() or "does not exist" in str(e).lower():
                    print(f"   - {column} 없음 (스킵)")
                    db.rollback()
                else:
                    print(f"   ! {column} 삭제 실패 (무시): {e}")
                    db.rollback()
        
        # 4. StudentRequirementStatus - 신 2-메트릭 컬럼 추가
        print("\n[4/4] StudentRequirementStatus 테이블 - 신 2-메트릭 추가...")
        new_fields = [
            ("curriculum_completion_score", "1학년 전공체계도 완성도"),
            ("related_courses_score", "유사과목 점수"),
            ("overall_score", "종합 점수")
        ]
        
        for field_name, description in new_fields:
            try:
                db.execute(text(f"ALTER TABLE student_requirement_status ADD COLUMN {field_name} DECIMAL(5,2) NULL"))
                db.commit()
                print(f"   ✓ {field_name} 추가 완료 ({description})")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"   - {field_name} 이미 존재함 (스킵)")
                    db.rollback()
                else:
                    raise
        
        # 5. 기존 평가 결과 초기화 (선택적)
        print("\n[완료] 기존 평가 결과 초기화...")
        try:
            db.execute(text("""
                UPDATE student_requirement_status 
                SET curriculum_completion_score = NULL,
                    related_courses_score = NULL,
                    overall_score = NULL,
                    is_satisfied = FALSE
            """))
            db.commit()
            print("   ✓ 평가 데이터 초기화 완료")
        except Exception as e:
            print(f"   ! 초기화 실패 (무시): {e}")
            db.rollback()
        
        print("\n" + "="*80)
        print("✅ 마이그레이션 완료!")
        print("="*80)
        print("\n최종 스키마:")
        print("  📊 Student:")
        print("     - current_gpa (학생 평점)")
        print("     - total_credits (총 이수 학점)")
        print("\n  📋 DepartmentEntryRequirement:")
        print("     - logic_operator (OR/AND 조건)")
        print("\n  🎯 StudentRequirementStatus (2-메트릭):")
        print("     - curriculum_completion_score (70% 가중치)")
        print("     - related_courses_score (30% 가중치)")
        print("     - overall_score (종합)")
        print("\n다음 단계:")
        print("  1. docker-compose restart")
        print("  2. docker exec fastapi_backend uv run python batch_evaluate_all.py")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_database()
