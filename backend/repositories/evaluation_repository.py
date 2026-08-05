"""
평가 흐름 애그리거트용 리포지토리.

라우터/서비스에 흩어져 있던 Student/Department/StudentRequirementStatus 조회를
의도가 드러나는 메서드 뒤로 캡슐화한다. 테스트는 db.query 체이닝을 흉내 내는 대신
이 리포지토리를 대역(fake/mock)으로 주입하면 된다.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from constants import LIONS_COLLEGE_ID
from models.models import Department, Student, StudentRequirementStatus


class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, student_id: int) -> Optional[Student]:
        return (
            self.db.query(Student)
            .filter(Student.student_id == student_id)
            .first()
        )

    def get_by_email(self, email: str) -> Optional[Student]:
        return self.db.query(Student).filter(Student.email == email).first()

    def get_many(self, student_ids: List[int]) -> List[Student]:
        return (
            self.db.query(Student)
            .filter(Student.student_id.in_(student_ids))
            .all()
        )

    def list_in_lions_college(self) -> List[Student]:
        """라이언스 칼리지 소속 학생 전체."""
        return (
            self.db.query(Student)
            .filter(Student.department_id == LIONS_COLLEGE_ID)
            .all()
        )


class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, department_id: int) -> Optional[Department]:
        return (
            self.db.query(Department)
            .filter(Department.id == department_id)
            .first()
        )

    def list_evaluation_targets(self) -> List[Department]:
        """평가 대상 학과(라이언스 칼리지 제외)."""
        return (
            self.db.query(Department)
            .filter(Department.id > LIONS_COLLEGE_ID)
            .all()
        )


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
