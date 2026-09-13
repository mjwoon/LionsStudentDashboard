"""배포된 커밋을 밖에서 식별할 수 있어야 한다.

배경: 어떤 커밋이 떠 있는지 확인할 방법이 없어, 배포 반영 여부를 API 동작 변화로
추측해야 했다(응답 스키마가 바뀌었는지 보고 역추론하는 식). Render가 컨테이너에
넣어주는 RENDER_GIT_COMMIT을 그대로 노출한다.
"""

import pytest
from fastapi.testclient import TestClient

import main
from lions_core.config import Settings

client = TestClient(main.app)


@pytest.fixture
def deployed(monkeypatch):
    """Render 환경을 흉내 낸다."""
    monkeypatch.setattr(
        main,
        "settings",
        Settings(render_git_commit="126d3f5aa1b2c3d4e5f6", render_git_branch="master"),
    )


def test_health_reports_deployed_commit(deployed):
    body = client.get("/health").json()

    assert body["status"] == "healthy"
    assert body["commit"] == "126d3f5"  # short SHA
    assert body["branch"] == "master"


def test_root_reports_deployed_commit(deployed):
    body = client.get("/").json()

    assert body["commit"] == "126d3f5"
    assert body["status"] == "running"


def test_health_omits_commit_outside_deployment(monkeypatch):
    """로컬·테스트에는 그 값이 없다 — 의미 없는 null을 남기지 않는다."""
    monkeypatch.setattr(main, "settings", Settings())

    body = client.get("/health").json()

    assert body == {"status": "healthy"}


def test_branch_omitted_when_only_commit_is_known(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings(render_git_commit="abcdef1234567"))

    body = client.get("/health").json()

    assert body["commit"] == "abcdef1"
    assert "branch" not in body
