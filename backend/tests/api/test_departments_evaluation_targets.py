"""GET /api/departments 의 평가 대상 필터 (실제 SQLite).

학생 상세의 '분석할 학과 선택' 드롭다운은 이 엔드포인트를 쓴다. 라이언스 칼리지의
세 계열(전계열·인문사회계열·자연계열)은 학생의 소속이지 진입 대상 전공이 아니므로
선택지에 나오면 안 된다. 다른 소비자를 위해 기본 동작(전체 반환)은 유지한다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from models.models import Base, College, Department

client = TestClient(app)


@pytest.fixture
def db():
    # TestClient는 별도 스레드에서 돈다. StaticPool로 같은 :memory: 연결을 공유하지 않으면
    # 라우터 쪽에서 빈 DB를 보게 된다.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(College(id=1, name="라이언스 칼리지"))
    session.add(College(id=3, name="소프트웨어융합대학"))
    session.add(Department(id=100, code="LIONS1", name="전계열", college_id=1))
    session.add(Department(id=101, code="LIONS2", name="인문사회계열", college_id=1))
    session.add(Department(id=102, code="LIONS3", name="자연계열", college_id=1))
    session.add(Department(id=300, code="CS_CS", name="컴퓨터학부", college_id=3))
    session.commit()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()


def _names(params=""):
    resp = client.get(f"/api/departments{params}")
    assert resp.status_code == 200
    return {d["name"] for d in resp.json()["departments"]}


def test_default_still_returns_every_department(db):
    """기존 소비자를 위해 기본 동작은 그대로 전체 반환."""
    assert _names() == {"전계열", "인문사회계열", "자연계열", "컴퓨터학부"}


def test_evaluation_targets_only_drops_all_lions_tracks(db):
    """평가 대상만 요청하면 라이언스 칼리지 세 계열이 모두 빠진다."""
    assert _names("?evaluation_targets_only=true") == {"컴퓨터학부"}
