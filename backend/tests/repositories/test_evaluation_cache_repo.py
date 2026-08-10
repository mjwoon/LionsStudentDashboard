"""
EvaluationCacheRepository.save_result 검증 (실제 SQLite).

평가 결과 캐시 쓰기 로직은 그동안 테스트가 없었다(서비스 테스트는 _save_evaluation_result를
목으로 대체). 쓰기 매핑을 리포지토리로 일원화(SSOT)하면서 실제 동작을 고정한다.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import Base, Department, Student, StudentRequirementStatus
from repositories import EvaluationCacheRepository


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
    db.add(Department(id=101, code="C1", name="D1"))
    db.add(
        Student(
            student_id=202400001,
            name="테스터",
            email="s@example.com",
            phone="010",
            department_id=101,
        )
    )
    db.commit()


def test_save_result_maps_fields_and_satisfaction(db):
    _seed(db)
    repo = EvaluationCacheRepository(db)

    result = {
        "curriculum_similar_rate": 10,
        "recommended_similar_rate": 20,
        "overall_score": 85.0,
        "analysis_json": {"x": 1},
        "evaluated_at": datetime.now(timezone.utc),
    }
    status = repo.save_result(202400001, 101, result)
    db.commit()

    assert float(status.overall_score) == 85.0
    assert float(status.curriculum_completion_score) == 10
    assert float(status.related_courses_score) == 20
    assert status.analysis_json == {"x": 1}
    assert status.is_satisfied is True  # 85 >= 70


def test_save_result_updates_existing_row(db):
    _seed(db)
    repo = EvaluationCacheRepository(db)

    base = {
        "curriculum_similar_rate": 10,
        "recommended_similar_rate": 20,
        "analysis_json": None,
        "evaluated_at": datetime.now(timezone.utc),
    }
    repo.save_result(202400001, 101, {**base, "overall_score": 85.0})
    db.commit()
    repo.save_result(202400001, 101, {**base, "overall_score": 50.0})
    db.commit()

    # 갱신이지 신규 아님
    assert db.query(StudentRequirementStatus).count() == 1
    row = db.query(StudentRequirementStatus).first()
    assert float(row.overall_score) == 50.0
    assert row.is_satisfied is False  # 50 < 70
