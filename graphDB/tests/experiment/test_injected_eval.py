"""RQ2 주입 평가 서비스 (루트 3.12 환경에서 실행: backend/lions_core 필요).

graphDB 3.11 환경에는 lions_core/services 가 없으므로 자동 skip 된다.
"""
import pytest

pytest.importorskip("lions_core")
pytest.importorskip("services.evaluation_service")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from lions_core.models import Base  # noqa: E402
from experiment.injected_eval import InjectedEvaluationService  # noqa: E402


def test_injection_overrides_graph_and_threshold():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    calls = {}

    def fake_sim(a, b):
        calls[(a, b)] = True
        return 0.75

    svc = InjectedEvaluationService(db, similarity_fn=fake_sim, threshold=0.72)
    assert svc._is_graph_available() is True
    assert svc._similarity_threshold == 0.72
    assert svc._get_similarity_from_graph("X", "Y") == 0.75
    assert ("X", "Y") in calls
    db.close()
