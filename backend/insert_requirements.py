"""
진입요건 데이터 입력 스크립트

necessary.md 파일의 진입요건을 DepartmentEntryRequirement 및 RequirementCourse 테이블에 입력
"""

import sys
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from models.database import Department, DepartmentEntryRequirement, RequirementCourse, GradeLevelEnum, Course

def wait_for_db():
    """데이터베이스 연결 대기"""
    import time
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    
    for i in range(30):
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            print("Database is ready!")
            return True
        except OperationalError:
            print(f"Database not ready, waiting... ({i+1}/30)")
            time.sleep(1)
    print("Database connection timeout!")
    return False


def get_course_code(db, course_name: str) -> str:
    """과목명으로 course_code 조회. 없으면 None 반환"""
    course = db.query(Course).filter(Course.course_name == course_name).first()
    if course:
        return course.course_code
    
    # 유사한 이름으로 재검색
    course = db.query(Course).filter(Course.course_name.like(f"%{course_name}%")).first()
    if course:
        return course.course_code
    
    return None


def get_department_id_by_name(db, dept_name: str) -> int:
    """학과 이름으로 ID 조회"""
    dept = db.query(Department).filter(Department.name.like(f"%{dept_name}%")).first()
    if dept:
        return dept.id
    raise ValueError(f"학과를 찾을 수 없습니다: {dept_name}")


def insert_entry_requirements(db):
    """진입요건 데이터 입력"""
    
    print("기존 진입요건 데이터 삭제...")
    db.query(RequirementCourse).delete()
    db.query(DepartmentEntryRequirement).delete()
    db.commit()
    
    print("진입요건 데이터 입력 시작...")
    
    # ========================================================================
    # 공학대학
    # ========================================================================
    
    # 전자공학부
    print("  - 전자공학부 진입요건 입력...")
    try:
        dept_id = get_department_id_by_name(db, "전자공학부")
        
        # "5개 과목 중 B 이상 2과목 OR A 이상 1과목" (OR 조건)
        req1 = DepartmentEntryRequirement(
            department_id=dept_id,
            admission_year=2026,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.B,
            required_count=2,
            requirement_text="아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수",
            is_alert_required=True,
            logic_operator="OR"  # OR 조건
        )
        db.add(req1)
        db.flush()
        
        # 요건 과목 추가
        requirement_courses = [
            "확률과통계",
            "미분적분학1",
            "일반물리학1",
            "미분적분학2",
            "일반물리학2"
        ]
        
        added_count = 0
        for course_name in requirement_courses:
            course_code = get_course_code(db, course_name)
            if course_code:
                req_course = RequirementCourse(
                    requirement_id=req1.id,
                    course_code=course_code
                )
                db.add(req_course)
                added_count += 1
            else:
                print(f"      ⚠ 과목을 찾을 수 없습니다: {course_name}")
        
        print(f"    ✓ 전자공학부: {added_count}/{len(requirement_courses)}개 과목 추가됨 (OR 조건)")
    
    except ValueError as e:
        print(f"    ✗ 전자공학부: {e}")
    
    # 산업경영공학과
    print("  - 산업경영공학과 진입요건 입력...")
    try:
        dept_id = get_department_id_by_name(db, "산업경영공학과")
        
        req2 = DepartmentEntryRequirement(
            department_id=dept_id,
            admission_year=2026,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.C,
            required_count=1,
            requirement_text="미분적분학1 C(2.0) 이상 필수",
            is_alert_required=True,
            logic_operator="AND"
        )
        db.add(req2)
        db.flush()
        
        course_code = get_course_code(db, "미분적분학1")
        if course_code:
            req_course = RequirementCourse(
                requirement_id=req2.id,
                course_code=course_code
            )
            db.add(req_course)
            print(f"    ✓ 산업경영공학과: 1개 과목 (AND 조건)")
        else:
            print(f"    ⚠ 산업경영공학과: 미분적분학1 과목을 찾을 수 없습니다")
    
    except ValueError as e:
        print(f"    ✗ 산업경영공학과: {e}")
    
    # ========================================================================
    # 첨단융합대학
    # ========================================================================
    
    # 바이오신약융합학부 - 분자의약전공
    print("  - 바이오신약융합학부(분자의약전공) 진입요건 입력...")
    try:
        # "분자의약" 포함하는 학과 찾기
        dept = db.query(Department).filter(Department.name.like("%분자의약%")).first()
        if not dept:
            print(f"    ✗ 분자의약전공을 찾을 수 없습니다")
        else:
            dept_id = dept.id
            
            req3 = DepartmentEntryRequirement(
                department_id=dept_id,
                admission_year=2026,
                requirement_group=1,
                target_grade_level=GradeLevelEnum.B,
                required_count=1,
                requirement_text="아래 2개 과목 중 B(3.0) 이상 1과목 필수",
                is_alert_required=True,
                logic_operator="AND"
            )
            db.add(req3)
            db.flush()
            
            requirement_courses = [
                "일반생물학1",
                "일반생물학2"
            ]
            
            added_count = 0
            for course_name in requirement_courses:
                course_code = get_course_code(db, course_name)
                if course_code:
                    req_course = RequirementCourse(
                        requirement_id=req3.id,
                        course_code=course_code
                    )
                    db.add(req_course)
                    added_count += 1
                else:
                    print(f"      ⚠ 과목을 찾을 수 없습니다: {course_name}")
            
            print(f"    ✓ 분자의약전공: {added_count}/{len(requirement_courses)}개 과목 추가됨 (AND 조건)")
    
    except Exception as e:
        print(f"    ✗ 분자의약전공: {e}")
    
    # ========================================================================
    # 커뮤니케이션&컬쳐대학
    # ========================================================================
    
    # 광고홍보학과
    print("  - 광고홍보학과 진입요건 입력...")
    try:
        dept_id = get_department_id_by_name(db, "광고홍보학과")
        
        req4 = DepartmentEntryRequirement(
            department_id=dept_id,
            admission_year=2026,
            requirement_group=1,
            target_grade_level=GradeLevelEnum.B,
            required_count=1,
            requirement_text="아래 5개 과목 중 B(3.0) 이상 1과목 필수",
            is_alert_required=True,
            logic_operator="AND"
        )
        db.add(req4)
        db.flush()
        
        requirement_courses = [
            "커뮤니케이션론",
            "광고원론",
            "홍보원론",
            "크리에이티브디자인",
            "전략적커뮤니케이션"
        ]
        
        added_count = 0
        for course_name in requirement_courses:
            course_code = get_course_code(db, course_name)
            if course_code:
                req_course = RequirementCourse(
                    requirement_id=req4.id,
                    course_code=course_code
                )
                db.add(req_course)
                added_count += 1
            else:
                print(f"      ⚠ 과목을 찾을 수 없습니다: {course_name}")
        
        print(f"    ✓ 광고홍보학과: {added_count}/{len(requirement_courses)}개 과목 추가됨 (AND 조건)")
    
    except ValueError as e:
        print(f"    ✗ 광고홍보학과: {e}")
    
    db.commit()
    print("\n진입요건 데이터 입력 완료!")
    
    # 통계 출력
    total_reqs = db.query(DepartmentEntryRequirement).count()
    total_courses = db.query(RequirementCourse).count()
    print(f"\n총 {total_reqs}개의 진입요건이 입력되었습니다.")
    print(f"총 {total_courses}개의 요건 과목이 입력되었습니다.")
    
    # 학과별 요건 수 출력
    print("\n학과별 진입요건:")
    reqs = db.query(DepartmentEntryRequirement).all()
    dept_req_count = {}
    for req in reqs:
        dept = db.query(Department).filter(Department.id == req.department_id).first()
        if dept:
            key = f"{dept.name} ({req.admission_year}년)"
            dept_req_count[key] = dept_req_count.get(key, 0) + 1
    
    for dept_name, count in sorted(dept_req_count.items()):
        or_reqs = db.query(DepartmentEntryRequirement).join(Department).filter(
            Department.name == dept_name.split(" (")[0],
            DepartmentEntryRequirement.logic_operator == "OR"
        ).count()
        operator_info = f" (OR 조건 {or_reqs}개)" if or_reqs > 0 else ""
        print(f"  - {dept_name}: {count}개 요건{operator_info}")


def main():
    """메인 함수"""
    print("=" * 70)
    print("진입요건 데이터 입력 스크립트")
    print("=" * 70)
    
    # 데이터베이스 연결 대기
    if not wait_for_db():
        print("데이터베이스 연결 실패")
        sys.exit(1)
    
    # 데이터베이스 초기화
    init_db()
    
    # 세션 생성
    db = SessionLocal()
    
    try:
        # 진입요건 데이터 입력
        insert_entry_requirements(db)
        
        print("\n" + "=" * 70)
        print("모든 작업이 완료되었습니다!")
        print("=" * 70)
    
    except Exception as e:
        print(f"\n오류 발생: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
