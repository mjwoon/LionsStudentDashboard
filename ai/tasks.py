"""
비동기 일괄 평가 Celery 태스크
Backend의 EvaluationService 로직을 Worker에서 비동기로 실행합니다.
"""

import logging
import sys
import os
from datetime import datetime
from celery_app import celery_app
from database import get_db_session
from services.ai_service import AIService

logger = logging.getLogger(__name__)

# Backend의 서비스 모듈을 import하기 위해 path 추가
BACKEND_PATH = os.getenv("BACKEND_PATH", "/backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

@celery_app.task(bind=True, name="rebuild_graph")
def rebuild_graph_task(self):
    """
    비동기 GraphDB 재구축 태스크
    """
    import subprocess
    import os

    self.update_state(
        state="PROGRESS",
        meta={
            "status": "GraphDB 재구축 시작...",
            "percent": 0
        }
    )

    try:
        logger.info("GraphDB 재구축 스크립트 실행 시작...")
        
        env = os.environ.copy()
        
        result = subprocess.run(
            ["uv", "run", "python", "quick_start.py"],
            cwd="/graphDB",
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            raise Exception(f"재구축 스크립트 실패: {result.stderr}")
            
        logger.info("GraphDB 재구축 스크립트 실행 완료")
        return {"success": True, "message": "GraphDB 재구축 완료"}
    except Exception as e:
        logger.error(f"GraphDB 재구축 오류: {str(e)}")
        return {"success": False, "error": str(e)}


@celery_app.task(bind=True, name="bulk_evaluate")
def bulk_evaluate_task(
    self,
    force_recalculate: bool = False,
    student_ids: list = None,
    department_ids: list = None
):
    """
    비동기 일괄 평가 태스크
    
    - 전체 학생 × 전체 학과 평가 수행
    - 매 건마다 Redis에 진행상황 업데이트
    - AI 총평 포함
    
    Args:
        force_recalculate: 기존 캐시 무시 여부
        student_ids: 특정 학생만 평가 (None이면 전체)
        department_ids: 특정 학과만 평가 (None이면 전체)
    """
    from models.models import Student, Department, StudentRequirementStatus
    from services.evaluation_service import EvaluationService
    
    ai_service = AIService()
    success_count = 0
    error_count = 0
    errors = []
    
    with get_db_session() as db:
        # 학생 목록
        students_query = db.query(Student)
        if student_ids:
            students_query = students_query.filter(Student.student_id.in_(student_ids))
        students = students_query.all()
        
        # 학과 목록
        departments_query = db.query(Department)
        if department_ids:
            departments_query = departments_query.filter(Department.id.in_(department_ids))
        else:
            departments_query = departments_query.filter(Department.id > 100)
        departments = departments_query.all()
        
        total = len(students) * len(departments)
        current = 0
        
        if total == 0:
            return {
                "success": True,
                "message": "평가할 대상이 없습니다.",
                "total_students": len(students),
                "total_departments": len(departments),
                "total_evaluations": 0,
                "success_count": 0,
                "error_count": 0,
                "errors": None
            }
        
        # 초기 상태 업데이트
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total,
                "percent": 0,
                "status": "평가 시작...",
                "success_count": 0,
                "error_count": 0
            }
        )
        
        for student in students:
            # 입학년도 추출
            try:
                admission_year = int(student.student_id[:4])
            except (ValueError, TypeError):
                admission_year = 2025
            
            for department in departments:
                current += 1
                
                try:
                    # 기존 캐시 확인
                    existing = db.query(StudentRequirementStatus).filter(
                        StudentRequirementStatus.student_id == student.id,
                        StudentRequirementStatus.department_id == department.id
                    ).first()
                    
                    if not force_recalculate and existing and existing.overall_score is not None:
                        success_count += 1
                    else:
                        # 평가 수행
                        evaluator = EvaluationService(db)
                        result = evaluator.evaluate_student(
                            student.id,
                            department.id,
                            admission_year,
                            save_to_db=False  # Worker가 직접 저장
                        )
                        
                        # AI 총평 생성
                        ai_summary = ai_service.generate_evaluation_summary(result)
                        
                        # analysis_json에 ai_summary 포함
                        analysis_json = result.get("analysis_json", {})
                        if ai_summary:
                            analysis_json["ai_summary"] = ai_summary
                        
                        # DB 저장/업데이트
                        if existing:
                            existing.is_satisfied = result.get("overall_score", 0) >= 70
                            existing.overall_score = result.get("overall_score", 0)
                            existing.analysis_json = analysis_json
                            existing.ai_summary = ai_summary
                            existing.calculated_at = datetime.utcnow()
                        else:
                            new_record = StudentRequirementStatus(
                                student_id=student.id,
                                department_id=department.id,
                                is_satisfied=result.get("overall_score", 0) >= 70,
                                overall_score=result.get("overall_score", 0),
                                analysis_json=analysis_json,
                                ai_summary=ai_summary,
                            )
                            db.add(new_record)
                        
                        success_count += 1
                
                except Exception as e:
                    error_count += 1
                    error_msg = f"학생 {student.student_id} - 학과 {department.name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"평가 오류: {error_msg}")
                
                # 진행상황 업데이트 (매 10건마다)
                if current % 10 == 0 or current == total:
                    percent = round((current / total) * 100, 1)
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": current,
                            "total": total,
                            "percent": percent,
                            "status": f"평가 중... ({current}/{total})",
                            "success_count": success_count,
                            "error_count": error_count
                        }
                    )
            
            # 학생 단위로 커밋 (메모리 관리)
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"커밋 실패 (학생 {student.student_id}): {e}")
    
    return {
        "success": True,
        "message": "대량 진단 완료",
        "total_students": len(students),
        "total_departments": len(departments),
        "total_evaluations": total,
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors if errors else None
    }
