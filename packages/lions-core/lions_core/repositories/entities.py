"""
범용 엔티티 리포지토리.

여러 라우터/서비스에서 반복되는 단순 엔티티 조회(Student, Department)를 캡슐화한다.
평가 캐시(StudentRequirementStatus)처럼 특정 애그리거트에 종속된 접근은
evaluation_repository 로 분리한다.
"""

from typing import List, Optional

from sqlalchemy import or_
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
        """라이언스 칼리지 소속 학생 전체.

        소속 계열은 전계열·인문사회계열·자연계열 셋으로 나뉘므로 학과 id 하나로는
        판정할 수 없다. 학과가 속한 단과대학으로 거른다.
        """
        return (
            self.db.query(Student)
            .join(Department, Student.department_id == Department.id)
            .filter(Department.college_id == LIONS_COLLEGE_ID)
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
        """평가 대상 학과(라이언스 칼리지 제외).

        라이언스 칼리지의 세 계열은 학생의 소속이지 진입 대상 전공이 아니다.
        단과대학이 비어 있는 학과는 라이언스 소속이라 단정할 수 없으므로 남긴다.
        """
        return (
            self.db.query(Department)
            .filter(
                or_(
                    Department.college_id.is_(None),
                    Department.college_id != LIONS_COLLEGE_ID,
                )
            )
            .all()
        )
