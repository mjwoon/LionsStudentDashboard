"""
평가 캐시 애그리거트용 리포지토리.

평가 결과 캐시(StudentRequirementStatus) 접근을 한 곳으로 모은다. 이 접근 로직은
현재 서비스/일괄 워커에도 중복되어 있으며, 향후 SSOT로 수렴할 지점이다.
"""

from typing import Dict, Optional

from sqlalchemy.orm import Session

from lions_core.constants import MIN_SATISFACTION_SCORE
from lions_core.models import StudentRequirementStatus


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

    def save_result(
        self,
        student_id: int,
        department_id: int,
        result: Dict,
        ai_summary: Optional[str] = None,
    ) -> StudentRequirementStatus:
        """평가 결과(result)를 캐시 레코드에 매핑해 기록한다(신규/갱신). commit은 호출자 책임.

        StudentRequirementStatus 쓰기의 단일 진실 원천(SSOT). 서비스/워커가 각자
        필드 매핑을 복제하지 않고 이 메서드를 재사용하도록 한다.

        ai_summary가 주어지면 컬럼과 analysis_json['ai_summary']에 함께 기록한다
        (AI 워커 경로 호환).
        """
        status = self.get_or_create(student_id, department_id)

        analysis_json = result.get('analysis_json')
        if ai_summary is not None:
            analysis_json = dict(analysis_json or {})
            analysis_json['ai_summary'] = ai_summary
            status.ai_summary = ai_summary

        status.curriculum_completion_score = result.get('curriculum_similar_rate', 0)
        status.related_courses_score = result.get('recommended_similar_rate', 0)
        status.overall_score = result['overall_score']
        status.analysis_json = analysis_json
        status.calculated_at = result['evaluated_at']
        status.is_satisfied = result['overall_score'] >= MIN_SATISFACTION_SCORE
        return status
