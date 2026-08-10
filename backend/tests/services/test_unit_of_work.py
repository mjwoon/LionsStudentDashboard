"""
Unit of Work + run_upsert(commit=False) 원자성 검증 (실제 SQLite).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import Base, College
from services.unit_of_work import unit_of_work
from services.upsert_processor import run_upsert


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _upsert_college(db, name, commit):
    return run_upsert(
        db,
        [{"name": name}],
        find_existing=lambda d, data: d.query(College).filter(College.name == data["name"]).first(),
        create_new=lambda d, data: College(name=data["name"]),
        update_existing=lambda d, existing, data: None,
        item_id_accessor=lambda data: data["name"],
        success_message="대학 데이터 업로드 완료",
        commit=commit,
    )


def test_uow_commits_all_on_success(db):
    with unit_of_work(db):
        _upsert_college(db, "A", commit=False)
        _upsert_college(db, "B", commit=False)
    assert db.query(College).count() == 2


def test_uow_rolls_back_all_on_error(db):
    with pytest.raises(RuntimeError):
        with unit_of_work(db):
            _upsert_college(db, "A", commit=False)
            _upsert_college(db, "B", commit=False)
            raise RuntimeError("boom")  # 그룹 도중 실패
    # 원자적: 앞서 추가된 것도 롤백
    assert db.query(College).count() == 0


def test_run_upsert_default_commits_standalone(db):
    resp = _upsert_college(db, "solo", commit=True)
    assert resp.uploaded_count == 1
    # 단독 커밋 경로 — 새 세션에서도 보이도록 커밋됨
    assert db.query(College).count() == 1


def test_uow_flag_defers_even_default_commit(db):
    """세션 플래그: UoW 안이면 commit=True(기본)여도 개별 커밋을 건너뛰어 원자성 보장.

    → 라우터는 upload_*를 그대로(기본 commit=True) 호출하고 본문만 with로 감싸면 됨.
    """
    with pytest.raises(RuntimeError):
        with unit_of_work(db):
            _upsert_college(db, "A", commit=True)
            raise RuntimeError("boom")
    assert db.query(College).count() == 0
