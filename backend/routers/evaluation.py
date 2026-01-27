"""
전공진입 적합도 평가 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from services.evaluation_service import MajorSuitabilityEvaluator
from models.database import StudentRequirementStatus, Student, Department
from models.schemas import (
    EvaluationResultResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    StudentEvaluationSummary
)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/student/{student_id}/department/{department_id}", response_model=EvaluationResultResponse)
def evaluate_student_for_department(
    student_id: str,
    department_id: int,
    admission_year: int = 2025,
    force_recalculate: bool = False,
    db: Session = Depends(get_db)
):
    """
    특정 학생의 특정 학과에 대한 진입 적합도 평가
    
    - **student_id**: 학생 학번
    - **department_id**: 평가할 학과 ID
    - **admission_year**: 입학년도 (진입요건 기준, 기본값: 2025)
    - **force_recalculate**: 강제 재계산 여부 (기본값: False, 캐시된 결과 사용)
    """
    # 학생 조회
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")
    
    # 강제 재계산이 아니면 캐시된 결과 먼저 확인
    if not force_recalculate:
        cached_result = db.query(StudentRequirementStatus).filter(
            StudentRequirementStatus.student_id == student.id,
            StudentRequirementStatus.department_id == department_id
        ).first()
        
        if cached_result and cached_result.analysis_json:
            return EvaluationResultResponse(**cached_result.analysis_json)
    
    # 새로 계산
    evaluator = MajorSuitabilityEvaluator(db)
    
    try:
        result = evaluator.evaluate_student_for_department(
            student.id, department_id, admission_year
        )
        
        # 결과 저장
        evaluator.save_evaluation_results([result])
        
        return EvaluationResultResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 중 오류 발생: {str(e)}")


@router.get("/student/{student_id}/all-departments")
def evaluate_student_for_all_departments(
    student_id: str,
    admission_year: int = 2025,
    db: Session = Depends(get_db)
):
    """
    특정 학생의 모든 학과에 대한 적합도 평가
    
    - **student_id**: 학생 학번
    - **admission_year**: 입학년도
    
    Returns:
        모든 학과에 대한 평가 결과 리스트 (적합도 순으로 정렬)
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")
    
    # 모든 학과 조회 (라이언스 칼리지 제외)
    departments = db.query(Department).filter(Department.id > 100).all()
    
    evaluator = MajorSuitabilityEvaluator(db)
    results = []
    
    for dept in departments:
        try:
            result = evaluator.evaluate_student_for_department(
                student.id, dept.id, admission_year
            )
            results.append(result)
        except Exception as e:
            print(f"학과 {dept.name} 평가 중 오류: {e}")
            continue
    
    # 적합도 점수로 정렬 (높은 순)
    results.sort(key=lambda x: x['overall_score'], reverse=True)
    
    # 결과 저장
    evaluator.save_evaluation_results(results)
    
    return {
        'student_id': student_id,
        'student_name': student.name,
        'total_departments': len(results),
        'evaluations': results
    }


@router.post("/batch/department/{department_id}", response_model=BatchEvaluationResponse)
def batch_evaluate_department(
    department_id: int,
    background_tasks: BackgroundTasks,
    admission_year: int = 2025,
    db: Session = Depends(get_db)
):
    """
    특정 학과에 대해 모든 학생 평가 (배치 처리)
    
    - **department_id**: 평가할 학과 ID
    - **admission_year**: 입학년도
    
    Note: 시간이 오래 걸릴 수 있으므로 백그라운드로 처리
    """
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail=f"학과 ID {department_id}를 찾을 수 없습니다.")
    
    evaluator = MajorSuitabilityEvaluator(db)
    
    # 동기적으로 실행 (빠른 응답을 위해)
    results = evaluator.batch_evaluate_all_students(department_id, admission_year)
    saved_count = evaluator.save_evaluation_results(results)
    
    return BatchEvaluationResponse(
        department_id=department_id,
        department_name=department.name,
        total_students=len(results),
        saved_count=saved_count,
        message=f"{department.name}에 대한 {saved_count}명의 학생 평가가 완료되었습니다."
    )


@router.post("/batch/all-departments")
def batch_evaluate_all_departments(
    background_tasks: BackgroundTasks,
    admission_year: int = 2025,
    limit_students: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    모든 학과에 대해 모든 학생 평가 (전체 배치 처리)
    
    - **admission_year**: 입학년도
    - **limit_students**: 처리할 학생 수 제한 (테스트용, None이면 전체)
    
    Warning: 매우 시간이 오래 걸립니다. 관리자 전용 기능입니다.
    """
    # 모든 학과 조회 (라이언스 칼리지 제외)
    departments = db.query(Department).filter(Department.id > 100).all()
    
    # 학생 조회
    students_query = db.query(Student)
    if limit_students:
        students_query = students_query.limit(limit_students)
    students = students_query.all()
    
    evaluator = MajorSuitabilityEvaluator(db)
    
    total_evaluations = 0
    results_by_department = {}
    
    for dept in departments:
        print(f"Processing department: {dept.name}")
        results = []
        
        for student in students:
            try:
                result = evaluator.evaluate_student_for_department(
                    student.id, dept.id, admission_year
                )
                results.append(result)
            except Exception as e:
                print(f"Error evaluating student {student.student_id} for {dept.name}: {e}")
                continue
        
        saved_count = evaluator.save_evaluation_results(results)
        results_by_department[dept.name] = {
            'department_id': dept.id,
            'evaluated': len(results),
            'saved': saved_count
        }
        total_evaluations += saved_count
    
    return {
        'total_departments': len(departments),
        'total_students': len(students),
        'total_evaluations': total_evaluations,
        'results_by_department': results_by_department,
        'message': f"총 {total_evaluations}건의 평가가 완료되었습니다."
    }


@router.get("/student/{student_id}/summary")
def get_student_evaluation_summary(
    student_id: str,
    db: Session = Depends(get_db)
):
    """
    학생의 저장된 평가 결과 요약 조회
    
    - **student_id**: 학생 학번
    
    Returns:
        저장된 평가 결과 요약 (적합도 상위 5개 학과)
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")
    
    # 저장된 평가 결과 조회
    evaluations = db.query(StudentRequirementStatus).filter(
        StudentRequirementStatus.student_id == student.id
    ).order_by(StudentRequirementStatus.overall_score.desc()).limit(10).all()
    
    if not evaluations:
        return {
            'student_id': student_id,
            'student_name': student.name,
            'total_evaluations': 0,
            'top_departments': [],
            'message': '아직 평가 결과가 없습니다. 평가를 먼저 실행하세요.'
        }
    
    # 학과 정보 포함
    top_departments = []
    for eval_result in evaluations[:5]:
        department = db.query(Department).filter(Department.id == eval_result.department_id).first()
        top_departments.append({
            'department_id': eval_result.department_id,
            'department_name': department.name if department else 'Unknown',
            'overall_score': eval_result.overall_score,
            'grade': eval_result.grade,
            'is_requirement_satisfied': eval_result.is_requirement_satisfied,
            'evaluated_at': eval_result.evaluated_at.isoformat() if eval_result.evaluated_at else None
        })
    
    return {
        'student_id': student_id,
        'student_name': student.name,
        'total_evaluations': len(evaluations),
        'top_departments': top_departments
    }


@router.delete("/cache/student/{student_id}")
def clear_student_evaluation_cache(
    student_id: str,
    db: Session = Depends(get_db)
):
    """
    특정 학생의 평가 결과 캐시 삭제
    
    - **student_id**: 학생 학번
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")
    
    deleted_count = db.query(StudentRequirementStatus).filter(
        StudentRequirementStatus.student_id == student.id
    ).delete()
    
    db.commit()
    
    return {
        'student_id': student_id,
        'deleted_count': deleted_count,
        'message': f'{deleted_count}개의 평가 결과가 삭제되었습니다.'
    }


@router.delete("/cache/all")
def clear_all_evaluation_cache(db: Session = Depends(get_db)):
    """
    모든 평가 결과 캐시 삭제 (관리자 전용)
    
    Warning: 모든 저장된 평가 결과가 삭제됩니다.
    """
    deleted_count = db.query(StudentRequirementStatus).delete()
    db.commit()
    
    return {
        'deleted_count': deleted_count,
        'message': f'총 {deleted_count}개의 평가 결과가 삭제되었습니다.'
    }
