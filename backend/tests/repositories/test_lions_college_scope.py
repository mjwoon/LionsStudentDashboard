"""라이언스 칼리지 범위 판정 검증 (실제 SQLite).

라이언스 칼리지(colleges.id=1)에는 학과가 3개 있다 — 전계열(100)·인문사회계열(101)·
자연계열(102). 이들은 학생의 '소속'이지 '진입 대상 전공'이 아니다.

기존 구현은 LIONS_COLLEGE_ID를 100(학과 id)으로 두고
  - 평가 대상   : Department.id > 100   → 101·102가 학과 추천 목록에 새어 들어갔다
  - 소속 학생   : Student.department_id == 100 → 101·102 소속 학생이 배치 평가에서 빠졌다
판정 기준을 '단과대학'으로 바로잡는다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import Base, College, Department, Student
from repositories import DepartmentRepository, StudentRepository


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _seed(db):
    db.add(College(id=1, name="라이언스 칼리지"))
    db.add(College(id=3, name="소프트웨어융합대학"))
    # 라이언스 칼리지 = 학생의 소속 계열 (진입 대상 전공이 아니다)
    db.add(Department(id=100, code="LIONS1", name="전계열", college_id=1))
    db.add(Department(id=101, code="LIONS2", name="인문사회계열", college_id=1))
    db.add(Department(id=102, code="LIONS3", name="자연계열", college_id=1))
    # 실제 진입 대상 전공
    db.add(Department(id=300, code="CS_CS", name="컴퓨터학부", college_id=3))
    db.add(Department(id=303, code="ICT_DATA", name="데이터인텔리전스전공", college_id=3))

    for i, dept in enumerate((100, 101, 102), start=1):
        db.add(
            Student(
                student_id=202600000 + i,
                name=f"학생{i}",
                email=f"s{i}@example.com",
                phone="010",
                department_id=dept,
            )
        )
    db.commit()


def test_evaluation_targets_exclude_every_lions_department(db):
    """전계열뿐 아니라 인문사회계열·자연계열도 학과 추천 대상이 아니다."""
    _seed(db)

    targets = DepartmentRepository(db).list_evaluation_targets()
    names = {d.name for d in targets}

    assert names == {"컴퓨터학부", "데이터인텔리전스전공"}
    assert "인문사회계열" not in names
    assert "자연계열" not in names


def test_lions_students_include_all_three_tracks(db):
    """라이언스 칼리지 학생은 소속 계열(100/101/102)과 무관하게 전부 포함된다."""
    _seed(db)

    students = StudentRepository(db).list_in_lions_college()

    assert {s.department_id for s in students} == {100, 101, 102}
    assert len(students) == 3


def test_department_without_college_stays_an_evaluation_target(db):
    """단과대학이 비어 있는 학과는 라이언스 소속이라 단정할 수 없으니 대상에 남긴다."""
    _seed(db)
    db.add(Department(id=900, code="ORPHAN", name="미배정학과", college_id=None))
    db.commit()

    names = {d.name for d in DepartmentRepository(db).list_evaluation_targets()}
    assert "미배정학과" in names
