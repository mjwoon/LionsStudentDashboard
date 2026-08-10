"""
범용 엔티티 리포지토리.

여러 라우터/서비스에서 반복되는 단순 엔티티 조회(Student, Department)를 캡슐화한다.
평가 캐시(StudentRequirementStatus)처럼 특정 애그리거트에 종속된 접근은
evaluation_repository 로 분리한다.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from lions_core.constants import LIONS_COLLEGE_ID
from lions_core.models import Department, Student


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
