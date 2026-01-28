"""
전체 학생 배치 평가 스크립트
모든 학생에 대해 평가를 실행하고 결과를 student_requirement_status 테이블에 저장합니다.
"""
import sys
from pathlib import Path
from datetime import datetime

# backend 폴더를 Python 경로에 추가
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from database import get_db
from models.database import Student, Department
from services.evaluation_service import EvaluationService


def batch_evaluate_all_students():
    """전체 학생에 대한 배치 평가 실행"""
    db: Session = next(get_db())
    
    try:
        print("🚀 전체 학생 배치 평가 시작\n")
        print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 모든 학생 조회
        students = db.query(Student).all()
        total_students = len(students)
        print(f"📊 총 학생 수: {total_students}명\n")
        
        # 모든 학과 조회
        departments = db.query(Department).all()
        print(f"🏫 총 학과 수: {len(departments)}개\n")
        print("=" * 60)
        
        # EvaluationService 인스턴스 생성
        eval_service = EvaluationService(db)
        
        # 통계 변수
        success_count = 0
        error_count = 0
        evaluation_results = []
        
        # 각 학생에 대해 소속 학과 평가
        for idx, student in enumerate(students, 1):
            try:
                # 진행 상황 표시
                if idx % 10 == 0 or idx == 1:
                    print(f"\n진행: {idx}/{total_students} ({idx/total_students*100:.1f}%)")
                
                # 학생의 소속 학과 정보 가져오기
                department = db.query(Department).filter(
                    Department.id == student.department_id
                ).first()
                
                if not department:
                    print(f"⚠️  {student.name} (ID: {student.student_id}): 소속 학과 없음")
                    error_count += 1
                    continue
                
                # 평가 실행 (save_to_db=True로 DB 저장)
                result = eval_service.evaluate_student(
                    student_id=student.id,
                    department_id=department.id,
                    save_to_db=True
                )
                
                # 결과 저장 (result는 dict 형태)
                evaluation_results.append({
                    'student_name': student.name,
                    'student_id': student.student_id,
                    'department_name': department.name,
                    'overall_score': result['overall_score'],
                    'grade': result['grade'],
                    'is_satisfied': result['overall_score'] >= 70.0
                })
                
                success_count += 1
                
                # 간단한 진행 상황 (10명마다 한 줄 출력)
                if idx % 10 == 0:
                    recent_scores = [r['overall_score'] for r in evaluation_results[-10:]]
                    avg_score = sum(recent_scores) / len(recent_scores)
                    print(f"✅ 최근 10명 평균: {avg_score:.2f}점")
                
            except Exception as e:
                print(f"❌ {student.name} (ID: {student.student_id}) 평가 실패: {str(e)}")
                error_count += 1
                continue
        
        # 결과 커밋 (이미 evaluate_student에서 커밋되었으므로 필요 없음)
        # db.commit()
        
        print("\n" + "=" * 60)
        print("📈 배치 평가 완료!\n")
        print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ 성공: {success_count}명")
        print(f"❌ 실패: {error_count}명")
        print(f"📊 총 처리: {success_count + error_count}명\n")
        
        # 점수 분포 통계
        if evaluation_results:
            scores = [r['overall_score'] for r in evaluation_results]
            print("📊 점수 분포:")
            print(f"   평균: {sum(scores)/len(scores):.2f}점")
            print(f"   최고: {max(scores):.2f}점")
            print(f"   최저: {min(scores):.2f}점")
            
            # 등급 분포
            grades = {}
            for r in evaluation_results:
                grade = r['grade']
                grades[grade] = grades.get(grade, 0) + 1
            
            print("\n📊 등급 분포:")
            for grade in ['A', 'B', 'C', 'D', 'F']:
                count = grades.get(grade, 0)
                percentage = (count / len(evaluation_results)) * 100
                bar = '█' * int(percentage / 2)
                print(f"   {grade}: {count:3d}명 ({percentage:5.1f}%) {bar}")
            
            # 진입요건 충족 여부
            satisfied_count = sum(1 for r in evaluation_results if r['is_satisfied'])
            unsatisfied_count = len(evaluation_results) - satisfied_count
            print(f"\n📊 진입요건 충족:")
            print(f"   충족: {satisfied_count}명 ({satisfied_count/len(evaluation_results)*100:.1f}%)")
            print(f"   미충족: {unsatisfied_count}명 ({unsatisfied_count/len(evaluation_results)*100:.1f}%)")
        
        # 상위 10명과 하위 10명 출력
        if evaluation_results:
            print("\n" + "=" * 60)
            print("🏆 상위 10명:")
            top_10 = sorted(evaluation_results, key=lambda x: x['overall_score'], reverse=True)[:10]
            for idx, r in enumerate(top_10, 1):
                print(f"   {idx:2d}. {r['student_name']:10s} ({r['department_name']:15s}) - {r['overall_score']:6.2f}점 ({r['grade']})")
            
            print("\n⚠️  하위 10명:")
            bottom_10 = sorted(evaluation_results, key=lambda x: x['overall_score'])[:10]
            for idx, r in enumerate(bottom_10, 1):
                print(f"   {idx:2d}. {r['student_name']:10s} ({r['department_name']:15s}) - {r['overall_score']:6.2f}점 ({r['grade']})")
        
    except Exception as e:
        print(f"\n❌ 배치 평가 중 오류 발생: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    batch_evaluate_all_students()
