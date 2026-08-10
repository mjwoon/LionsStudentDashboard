"""
평가 캐시 행정 서비스.

AdminService(God-object)에서 '평가 캐시' 책임 — 대량 진단 오케스트레이션과
캐시 통계/삭제 — 를 분리한 것. 업로드/데이터 관리 책임과 변경 이유가 다르다.

벤치마크(BENCHMARK.md) 반영:
- B: EvaluationService를 배치 루프 밖에서 1회만 생성해 인스턴스 캐시(교육과정/유사도)를
     배치 전체에서 재사용(이전에는 학생×학과마다 재생성되어 전체 테이블을 반복 로드).
- D: 캐시 존재 확인을 EvaluationCacheRepository로 일원화.
"""

import logging
from typing import Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.models import Department, Student, StudentRequirementStatus
from models.schemas import (
    BulkEvaluationRequest,
    BulkEvaluationResponse,
    CachedEvaluationStats,
)
from repositories import EvaluationCacheRepository
from services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)


class EvaluationAdminService:
    """대량 진단 실행 및 진단 결과 캐시 관리."""

    @staticmethod
    def bulk_evaluate(
        db: Session, request: BulkEvaluationRequest
    ) -> BulkEvaluationResponse:
        """대량 진단 실행 및 결과 캐싱."""
        success_count = 0
        error_count = 0
        errors = []

        try:
            students_query = db.query(Student)
            if request.student_ids:
                students_query = students_query.filter(
                    Student.student_id.in_(request.student_ids)
                )
            students = students_query.all()

            departments_query = db.query(Department)
            if request.department_ids:
                departments_query = departments_query.filter(
                    Department.id.in_(request.department_ids)
                )
            departments = departments_query.all()

            total_evaluations = len(students) * len(departments)

            # [벤치마크 B] 루프 밖에서 1회 생성 — 인스턴스 캐시를 배치 전체에서 재사용
            evaluator = EvaluationService(db)
            cache_repo = EvaluationCacheRepository(db)

            for student in students:
                # 입학년도 계산 (학번 앞 4자리). student_id는 Integer이므로 str 변환 필요.
                try:
                    admission_year = int(str(student.student_id)[:4])
                except (ValueError, TypeError):
                    admission_year = 2025  # 기본값

                for department in departments:
                    try:
                        # [벤치마크 D] 캐시 존재 확인은 리포지토리로 일원화
                        existing_cache = cache_repo.get(student.student_id, department.id)

                        if request.force_recalculate or not existing_cache:
                            evaluator.evaluate_student(
                                student_id=student.student_id,
                                department_id=department.id,
                                admission_year=admission_year,
                                save_to_db=True,
                            )
                            success_count += 1
                        else:
                            success_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append(
                            f"학생 {student.student_id} - 학과 {department.name}: {str(e)}"
                        )
                        logger.error(
                            f"진단 오류 - 학생: {student.student_id}, "
                            f"학과: {department.name}, 오류: {str(e)}"
                        )

            db.commit()

            return BulkEvaluationResponse(
                success=True,
                message="대량 진단 완료",
                total_students=len(students),
                total_departments=len(departments),
                total_evaluations=total_evaluations,
                success_count=success_count,
                error_count=error_count,
                errors=errors if errors else None,
            )

        except Exception as e:
            db.rollback()
            logger.error(f"대량 진단 오류: {str(e)}")
            return BulkEvaluationResponse(
                success=False,
                message=f"대량 진단 실패: {str(e)}",
                total_students=0,
                total_departments=0,
                total_evaluations=0,
                success_count=0,
                error_count=0,
                errors=[str(e)],
            )

    @staticmethod
    def get_cached_evaluation_stats(db: Session) -> CachedEvaluationStats:
        """캐시된 진단 결과 통계 조회."""
        try:
            total_cached = db.query(StudentRequirementStatus).count()

            cached_by_department_query = (
                db.query(
                    Department.name,
                    func.count(StudentRequirementStatus.id).label("count"),
                )
                .join(
                    StudentRequirementStatus,
                    Department.id == StudentRequirementStatus.department_id,
                )
                .group_by(Department.name)
                .all()
            )
            cached_by_department = {
                dept_name: count for dept_name, count in cached_by_department_query
            }

            last_update_result = db.query(
                func.max(StudentRequirementStatus.calculated_at)
            ).scalar()

            return CachedEvaluationStats(
                total_cached=total_cached,
                cached_by_department=cached_by_department,
                last_update=last_update_result,
            )

        except Exception as e:
            logger.error(f"통계 조회 오류: {str(e)}")
            return CachedEvaluationStats(
                total_cached=0, cached_by_department={}, last_update=None
            )

    @staticmethod
    def clear_cached_evaluations(
        db: Session, department_id: Optional[int] = None
    ) -> Dict:
        """캐시된 진단 결과 삭제."""
        try:
            query = db.query(StudentRequirementStatus)
            if department_id:
                query = query.filter(
                    StudentRequirementStatus.department_id == department_id
                )

            deleted_count = query.delete()
            db.commit()

            return {
                "success": True,
                "message": f"{deleted_count}개의 캐시된 진단 결과를 삭제했습니다.",
                "deleted_count": deleted_count,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"캐시 삭제 오류: {str(e)}")
            return {
                "success": False,
                "message": f"캐시 삭제 실패: {str(e)}",
                "deleted_count": 0,
            }
