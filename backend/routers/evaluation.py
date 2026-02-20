"""
전공진입 적합도 평가 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from services.evaluation_service import EvaluationService
from models.models import StudentRequirementStatus, Student, Department

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/student/{student_id}/department/{department_id}")
def evaluate_student_for_department(
    student_id: str,
    department_id: int,
    admission_year: int = 2026,
    force_recalculate: bool = False,
    db: Session = Depends(get_db)
):
    """
    특정 학생의 특정 학과에 대한 진입 적합도 평가 (3개 메트릭)
    """
    # 학생 조회 (student_id is now PK)
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")
    
    # 강제 재계산이 아니면 캐시된 결과 먼저 확인
    if not force_recalculate:
        cached_result = db.query(StudentRequirementStatus).filter(
            StudentRequirementStatus.student_id == student.student_id,
            StudentRequirementStatus.department_id == department_id
        ).first()
        
        if cached_result and cached_result.overall_score is not None:
            # 체계도 상세 정보 추가
            evaluator = EvaluationService(db)
            curriculum_details = evaluator.get_curriculum_details(student.student_id, department_id)
            
            # analysis_json에서 상세 정보 추출
            analysis = cached_result.analysis_json or {}
            entry_req = analysis.get("entry_requirement", {})
            recommended = analysis.get("recommended_courses", {})
            curriculum = analysis.get("curriculum_completion", {})
            
            return {
                "student_id": student_id,
                "department_id": department_id,
                # 진입요건 충족
                "entry_requirement_score": entry_req.get("score", 100.0),
                # 권장과목 이수
                "recommended_exact_rate": recommended.get("exact_rate", 0),
                "recommended_similar_rate": recommended.get("similar_rate", 0),
                # 교육과정 이수
                "curriculum_exact_rate": curriculum.get("exact_rate", 0),
                "curriculum_similar_rate": curriculum.get("similar_rate", 0),
                # 종합
                "overall_score": float(cached_result.overall_score or 0),
                "grade": 'A' if cached_result.overall_score >= 90 else 'B' if cached_result.overall_score >= 80 else 'C' if cached_result.overall_score >= 70 else 'D' if cached_result.overall_score >= 60 else 'F',
                "summary_message": "진입요건 충족" if cached_result.is_satisfied else "추가 노력 필요",
                "evaluated_at": cached_result.calculated_at.isoformat() if cached_result.calculated_at else None,
                "cached": True,
                "analysis_json": analysis,
                "ai_summary": analysis.get("ai_summary", None),
                "curriculum_details": curriculum_details
            }
    
    # 새로 계산
    evaluator = EvaluationService(db)
    
    try:
        result = evaluator.evaluate_student(
            student.student_id, department_id, admission_year, save_to_db=True
        )
        result["cached"] = False
        
        # 체계도 상세 정보 추가
        curriculum_details = evaluator.get_curriculum_details(student.student_id, department_id)
        result["curriculum_details"] = curriculum_details
        
        return result
    
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
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")
    
    # 모든 학과 조회 (라이언스 칼리지 제외)
    departments = db.query(Department).filter(Department.id > 100).all()
    
    evaluator = EvaluationService(db)
    results = []
    
    for dept in departments:
        try:
            result = evaluator.evaluate_student(
                student.student_id, dept.id, admission_year, save_to_db=True
            )
            results.append(result)
        except Exception as e:
            print(f"학과 {dept.name} 평가 실패: {e}")
            continue
    
    # 종합 점수 기준 내림차순 정렬
    results.sort(key=lambda x: x['overall_score'], reverse=True)
    
    return {
        "student_id": student_id,
        "total_departments": len(results),
        "results": results
    }


@router.post("/batch/department/{department_id}")
def batch_evaluate_department(
    department_id: int,
    student_ids: Optional[List[str]] = None,
    admission_year: int = 2025,
    db: Session = Depends(get_db)
):
    """
    특정 학과에 대해 여러 학생을 일괄 평가
    """
    # 학과 확인
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail=f"학과 ID {department_id}를 찾을 수 없습니다.")
    
    # 학생 목록 조회
    if student_ids:
        students = db.query(Student).filter(Student.student_id.in_(student_ids)).all()
    else:
        students = db.query(Student).filter(Student.department_id == 100).all()  # 라이언스 칼리지 학생들
    
    if not students:
        raise HTTPException(status_code=404, detail="평가할 학생이 없습니다.")
    
    evaluator = EvaluationService(db)
    results = evaluator.batch_evaluate_students(
        [s.student_id for s in students],
        department_id,
        admission_year
    )
    
    return {
        "department_id": department_id,
        "department_name": department.name,
        "total_evaluated": len(results),
        "results": results
    }
