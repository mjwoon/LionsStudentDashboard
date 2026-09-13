"""희망전공 조사 업로드가 제출일을 받는다.

운영 DB를 재구축할 때 설문 응답은 백업에서 복원했지만 제출일만 돌아오지 않았다.
업로드 스키마에 날짜 필드가 없어 survey_date가 복원 시점으로 덮였다. 값은 백업에
남아 있으니 넣을 수 있게만 해두면 된다.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import Base, College, Department, MajorSurvey, Student
from models.schemas.uploads import MajorSurveyDataUpload
from services.upload_service import UploadService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(College(id=1, name="공과대학"))
    s.add(Department(id=204, college_id=1, name="전자공학부", code="ELEC"))
    s.add(Department(id=207, college_id=1, name="산업경영공학과", code="IE"))
    s.add(Student(student_id=2026000001, name="테스트", email="t@example.com",
                  phone="010-0000-0000", department_id=204))
    s.commit()
    yield s
    s.close()


def _row(**over):
    base = {
        "student_id": 2026000001, "survey_round_id": 1,
        "first_choice_id": 204, "second_choice_id": 207, "decision_scale": 5,
    }
    base.update(over)
    return MajorSurveyDataUpload(**base)


def _only_survey(session):
    return session.query(MajorSurvey).one()


def test_survey_date_is_stored_when_given(session):
    UploadService.upload_major_surveys(session, [_row(survey_date="2026-08-10")])
    saved = _only_survey(session)
    assert saved.survey_date.strftime("%Y-%m-%d") == "2026-08-10"


def test_naive_date_is_treated_as_utc(session):
    """DB 컬럼이 timezone-aware라 naive로 넣으면 방언에 따라 하루가 밀 수 있다."""
    parsed = _row(survey_date="2026-08-10").survey_date
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


def test_korean_alias_is_accepted(session):
    assert _row(**{"제출일": "2026-08-10"}).survey_date.strftime("%Y-%m-%d") == "2026-08-10"


def test_missing_date_falls_back_to_default(session):
    """날짜 열이 없는 기존 CSV는 그대로 동작해야 한다."""
    UploadService.upload_major_surveys(session, [_row()])
    assert _only_survey(session).survey_date is not None


def test_missing_date_does_not_wipe_existing(session):
    """날짜 없는 CSV로 덮어쓸 때 이미 들어 있던 제출일을 지우면 안 된다."""
    UploadService.upload_major_surveys(session, [_row(survey_date="2026-08-10")])
    UploadService.upload_major_surveys(session, [_row(decision_scale=3)])
    saved = _only_survey(session)
    assert saved.decision_scale == 3                              # 갱신은 됐고
    assert saved.survey_date.strftime("%Y-%m-%d") == "2026-08-10"  # 날짜는 보존된다


def test_date_is_updated_when_given_on_existing_row(session):
    UploadService.upload_major_surveys(session, [_row(survey_date="2026-08-10")])
    UploadService.upload_major_surveys(session, [_row(survey_date="2026-09-01")])
    assert _only_survey(session).survey_date.strftime("%Y-%m-%d") == "2026-09-01"


def test_datetime_with_time_is_preserved(session):
    UploadService.upload_major_surveys(
        session, [_row(survey_date="2026-08-10T13:45:00Z")]
    )
    saved = _only_survey(session)
    assert saved.survey_date.strftime("%Y-%m-%dT%H:%M:%S") == "2026-08-10T13:45:00"
