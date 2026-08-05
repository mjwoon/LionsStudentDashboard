"""
평가 캐시 애그리거트용 리포지토리.

평가 결과 캐시(StudentRequirementStatus) 접근을 한 곳으로 모은다. 이 접근 로직은
현재 서비스/일괄 워커에도 중복되어 있으며, 향후 SSOT로 수렴할 지점이다.
"""

from typing import Optional

from sqlalchemy.orm import Session

from models.models import StudentRequirementStatus


class EvaluationCacheRepository:
    """StudentRequirementStatus(평가 결과 캐시) 접근."""

    def __init__(self, db: Session):
        self.db = db

    def get(
        self, student_id: int, department_id: int
    ) -> Optional[StudentRequirementStatus]:
        return (
            self.db.query(StudentRequirementStatus)
            .filter(
                StudentRequirementStatus.student_id == student_id,
                StudentRequirementStatus.department_id == department_id,
            )
            .first()
        )

    def get_or_create(
        self, student_id: int, department_id: int
    ) -> StudentRequirementStatus:
        """기존 캐시 레코드를 찾고, 없으면 새로 만들어 세션에 추가한다(commit은 호출자 책임)."""
        status = self.get(student_id, department_id)
        if status is None:
            status = StudentRequirementStatus(
                student_id=student_id, department_id=department_id
            )
            self.db.add(status)
        return status
