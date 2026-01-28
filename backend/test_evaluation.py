"""
평가 알고리즘 테스트 스크립트

특정 학생(강우수, 강보통, 강고민)으로 평가 알고리즘 검증
"""

from database import SessionLocal
from services.evaluation_service import EvaluationService
from models.database import Student, Department, DepartmentEntryRequirement
import sys


def print_header(title: str):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_student_info(db, student_id: int):
    """학생 정보 출력"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        print(f"❌ 학생 ID {student_id}를 찾을 수 없습니다.")
        return None
    
    print(f"\n👤 학생 정보:")
    print(f"   - 이름: {student.name}")
    print(f"   - 학번: {student.student_id}")
    print(f"   - 현재 GPA: {student.current_gpa}")
    print(f"   - 이수 학점: {student.total_credits}")
    
    return student


def print_evaluation_result(result: dict):
    """평가 결과 출력"""
    print(f"\n📊 평가 결과 ({result['department_name']}):")
    print(f"   - GPA 점수: {result['gpa_score']}/100 (가중치 25%)")
    print(f"   - 필수과목 점수: {result['required_courses_score']}/100 (가중치 30%)")
    print(f"   - 권장과목 이수 점수: {result['recommended_completion_score']}/100 (가중치 15%)")
    print(f"   - 권장과목 학점 점수: {result['recommended_grade_score']}/100 (가중치 15%)")
    print(f"   - 교육과정 완성도: {result['curriculum_completion_score']}/100 (가중치 15%)")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   🎯 종합 점수: {result['overall_score']}/100")
    
    # 등급 판정
    score = result['overall_score']
    if score >= 90:
        grade = "A (매우 적합)"
    elif score >= 80:
        grade = "B (적합)"
    elif score >= 70:
        grade = "C (보통)"
    elif score >= 60:
        grade = "D (노력 필요)"
    else:
        grade = "F (부적합)"
    
    print(f"   📈 적합도 등급: {grade}")


def test_specific_students():
    """특정 학생 3명 테스트"""
    print_header("단계 2: 특정 학생으로 알고리즘 검증")
    
    db = SessionLocal()
    try:
        # 평가 서비스 초기화
        evaluation_service = EvaluationService(db)
        
        # 테스트 대상 학생
        test_students = [
            {"name": "강우수", "student_id": "2025123001"},
            {"name": "강보통", "student_id": "2025123002"},
            {"name": "강고민", "student_id": "2025123003"}
        ]
        
        # 평가할 학과 (데이터인텔리전스전공)
        dept_name = "데이터인텔리전스전공"
        department = db.query(Department).filter(
            Department.name.like(f"%{dept_name}%")
        ).first()
        
        if not department:
            print(f"❌ 학과 '{dept_name}'를 찾을 수 없습니다.")
            return
        
        print(f"\n🎓 평가 대상 학과: {department.name} (ID: {department.id})")
        
        # 진입요건 확인
        requirements = db.query(DepartmentEntryRequirement).filter(
            DepartmentEntryRequirement.department_id == department.id
        ).all()
        
        if requirements:
            print(f"\n📋 진입요건:")
            for req in requirements:
                print(f"   - {req.requirement_text}")
                print(f"     (logic_operator: {req.logic_operator}, required_count: {req.required_count})")
        else:
            print("\n⚠️  진입요건이 설정되지 않았습니다.")
        
        # 각 학생 평가
        for test_student in test_students:
            student = db.query(Student).filter(
                Student.student_id == test_student["student_id"]
            ).first()
            
            if not student:
                print(f"\n❌ {test_student['name']} ({test_student['student_id']})를 찾을 수 없습니다.")
                continue
            
            print("\n" + "-" * 80)
            print_student_info(db, student.id)
            
            # 평가 실행
            try:
                result = evaluation_service.evaluate_student(
                    student_id=student.id,
                    department_id=department.id,
                    admission_year=2025,
                    save_to_db=True
                )
                print_evaluation_result(result)
            except Exception as e:
                print(f"\n❌ 평가 실패: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_multiple_departments():
    """여러 학과에 대해 평가 테스트"""
    print_header("다중 학과 평가 테스트")
    
    db = SessionLocal()
    try:
        evaluation_service = EvaluationService(db)
        
        # 강우수 학생
        student = db.query(Student).filter(
            Student.student_id == "2025123001"
        ).first()
        
        if not student:
            print("❌ 강우수 학생을 찾을 수 없습니다.")
            return
        
        print_student_info(db, student.id)
        
        # 진입요건이 있는 학과들
        dept_names = ["전자공학부", "산업경영공학과", "분자의약전공", "광고홍보학과"]
        
        for dept_name in dept_names:
            dept = db.query(Department).filter(
                Department.name.like(f"%{dept_name}%")
            ).first()
            
            if not dept:
                print(f"\n⚠️  '{dept_name}'를 찾을 수 없습니다.")
                continue
            
            print(f"\n{'─' * 80}")
            try:
                result = evaluation_service.evaluate_student(
                    student_id=student.id,
                    department_id=dept.id,
                    admission_year=2026,
                    save_to_db=False
                )
                print_evaluation_result(result)
            except Exception as e:
                print(f"❌ {dept.name} 평가 실패: {e}")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--multi":
        test_multiple_departments()
    else:
        test_specific_students()
