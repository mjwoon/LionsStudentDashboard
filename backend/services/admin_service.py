"""
데이터 관리 서비스.

업로드는 UploadService, 대량평가/캐시는 EvaluationAdminService로 분리되었고,
여기에는 전체 데이터 삭제만 남는다(FK 순서 준수가 필요한 파괴적 관리 작업).
"""

import logging

from sqlalchemy.orm import Session

from models.models import (
    Student, Course, Department, StudentCourse,
    StudentRequirementStatus, College, Advisor,
    Curriculum, CourseRecommendation, DepartmentEntryRequirement,
    MajorSurvey, RequirementCourse,
)

logger = logging.getLogger(__name__)


class AdminService:
    """데이터 관리(전체 삭제)."""

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
