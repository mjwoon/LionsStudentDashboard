"""
관리자용 서비스 로직 (파사드).

세부 책임은 분리됨:
- 대량 데이터 업로드 → services.upload_service.UploadService
- 대량 진단/캐시 관리 → services.evaluation_admin_service.EvaluationAdminService
AdminService는 기존 호출부 호환을 위한 얇은 파사드로, 업로드 메서드를 재노출하고
평가/캐시 메서드를 위임하며, 전체 데이터 삭제만 직접 보유한다.
"""

import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from models.models import (
    Student, Course, Department, StudentCourse,
    StudentRequirementStatus, College, Advisor,
    Curriculum, CourseRecommendation, DepartmentEntryRequirement,
    MajorSurvey, RequirementCourse,
)
from models.schemas import (
    BulkEvaluationRequest, BulkEvaluationResponse, CachedEvaluationStats,
)
from services.evaluation_admin_service import EvaluationAdminService
from services.upload_service import UploadService

logger = logging.getLogger(__name__)


class AdminService:
    """관리자 기능 파사드."""

    # --- 업로드: UploadService로 분리, 기존 호출부 호환 위해 재노출 ---
    upload_colleges = staticmethod(UploadService.upload_colleges)
    upload_advisors = staticmethod(UploadService.upload_advisors)
    upload_departments = staticmethod(UploadService.upload_departments)
    upload_major_surveys = staticmethod(UploadService.upload_major_surveys)
    upload_courses = staticmethod(UploadService.upload_courses)
    upload_students = staticmethod(UploadService.upload_students)
    upload_enrollments = staticmethod(UploadService.upload_enrollments)
    upload_curriculums = staticmethod(UploadService.upload_curriculums)
    upload_recommendations = staticmethod(UploadService.upload_recommendations)
    upload_requirements = staticmethod(UploadService.upload_requirements)
    upload_requirement_courses = staticmethod(UploadService.upload_requirement_courses)

    @staticmethod
    def bulk_evaluate(db: Session, request: BulkEvaluationRequest) -> BulkEvaluationResponse:
        """대량 진단 실행 및 결과 캐싱 (EvaluationAdminService로 위임)."""
        return EvaluationAdminService.bulk_evaluate(db, request)

    @staticmethod
    def get_cached_evaluation_stats(db: Session) -> CachedEvaluationStats:
        """캐시된 진단 결과 통계 조회 (EvaluationAdminService로 위임)."""
        return EvaluationAdminService.get_cached_evaluation_stats(db)

    @staticmethod
    def clear_cached_evaluations(db: Session, department_id: Optional[int] = None) -> Dict:
        """캐시된 진단 결과 삭제 (EvaluationAdminService로 위임)."""
        return EvaluationAdminService.clear_cached_evaluations(db, department_id)

    @staticmethod
    def delete_all_data(db: Session) -> dict:
        """모든 업로드 데이터 삭제 (FK 순서 준수)"""
        try:
            db.query(StudentRequirementStatus).delete()
            db.query(MajorSurvey).delete()
            db.query(StudentCourse).delete()
            db.query(RequirementCourse).delete()
            db.query(CourseRecommendation).delete()
            db.query(Curriculum).delete()
            db.query(DepartmentEntryRequirement).delete()
            db.query(Student).delete()
            db.query(Advisor).delete()
            db.query(Course).delete()
            db.query(Department).delete()
            db.query(College).delete()
            db.commit()
            return {"success": True, "message": "모든 데이터가 삭제되었습니다."}
        except Exception as e:
            db.rollback()
            logger.error(f"전체 데이터 삭제 오류: {str(e)}")
            return {"success": False, "message": f"삭제 실패: {str(e)}"}
