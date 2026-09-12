"""
전공진입 적합도 평가 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from constants import classify_grade
from services.evaluation_service import EvaluationService
from repositories import (
    StudentRepository,
    DepartmentRepository,
    EvaluationCacheRepository,
)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/student/{student_id}/department/{department_id}")
def evaluate_student_for_department(
    student_id: int,
    department_id: int,
    admission_year: Optional[int] = None,
    force_recalculate: bool = False,
    db: Session = Depends(get_db)
):
    """
    특정 학생의 특정 학과에 대한 진입 적합도 평가 (3개 메트릭)
    """
    # 학생 조회 (student_id is now PK)
    student = StudentRepository(db).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")

    # 강제 재계산이 아니면 캐시된 결과 먼저 확인
    if not force_recalculate:
        cached_result = EvaluationCacheRepository(db).get(student.student_id, department_id)
        
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
                "grade": classify_grade(cached_result.overall_score),
                # 캐시는 overall_score가 not None일 때만 사용되므로 평가 가능한 건이지만,
                # 응답 계약을 새 계산 경로와 맞춰 화면이 한 가지 형태만 다루게 한다.
                "is_evaluable": analysis.get("overall", {}).get("is_evaluable", True),
                "summary_message": "진입요건 충족" if cached_result.is_satisfied else "추가 노력 필요",
                "evaluated_at": cached_result.calculated_at.isoformat() if cached_result.calculated_at else None,
                "cached": True,
                "analysis_json": analysis,
                "ai_summary": analysis.get("ai_summary", None),
                "curriculum_details": curriculum_details
            }
    
    # 새로 계산 (admission_year 미지정 시 학번에서 도출)
    evaluator = EvaluationService(db)
    effective_admission_year = (
        admission_year
        if admission_year is not None
        else EvaluationService.get_admission_year_from_student_id(str(student.student_id))
    )

    try:
        result = evaluator.evaluate_student(
            student.student_id, department_id, effective_admission_year, save_to_db=True
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
    student_id: int,
    admission_year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    특정 학생의 모든 학과에 대한 적합도 평가
    """
    student = StudentRepository(db).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"학번 {student_id}를 찾을 수 없습니다.")

    # 모든 학과 조회 (라이언스 칼리지 제외)
    departments = DepartmentRepository(db).list_evaluation_targets()
    
    evaluator = EvaluationService(db)
    effective_admission_year = (
        admission_year
        if admission_year is not None
        else EvaluationService.get_admission_year_from_student_id(str(student.student_id))
    )
    results = []

    for dept in departments:
        try:
            result = evaluator.evaluate_student(
                student.student_id, dept.id, effective_admission_year, save_to_db=True
            )
            results.append(result)
        except Exception as e:
            print(f"학과 {dept.name} 평가 실패: {e}")
            continue
    
    # 평가 근거가 있는 학과만 순위를 매긴다.
    # 근거 0개 학과는 어떤 학생에게나 같은 값이 나와 순위 정보가 없고, 그럼에도
    # 과거에는 공허참 100점으로 추천 1위를 차지했다. 점수 없이 뒤에 붙인다.
    evaluable = [r for r in results if r.get('is_evaluable', True)]
    not_evaluable = [r for r in results if not r.get('is_evaluable', True)]
    evaluable.sort(key=lambda x: x['overall_score'], reverse=True)
    not_evaluable.sort(key=lambda x: x['department_name'])

    return {
        "student_id": student_id,
        "total_departments": len(results),
        "evaluable_count": len(evaluable),
        "not_evaluable_count": len(not_evaluable),
        "results": evaluable + not_evaluable
    }


@router.post("/batch/department/{department_id}")
def batch_evaluate_department(
    department_id: int,
    student_ids: Optional[List[int]] = None,
    admission_year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    특정 학과에 대해 여러 학생을 일괄 평가
    """
    # 학과 확인
    department = DepartmentRepository(db).get(department_id)
    if not department:
        raise HTTPException(status_code=404, detail=f"학과 ID {department_id}를 찾을 수 없습니다.")

    # 학생 목록 조회
    student_repo = StudentRepository(db)
    if student_ids:
        students = student_repo.get_many(student_ids)
    else:
        students = student_repo.list_in_lions_college()  # 라이언스 칼리지 학생들
    
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
