"""대량 진단 job 상태 조회가 '없는 job'과 '큐에 남은 job'을 구분한다.

예전에는 Redis에 결과 키가 없으면 무조건 PENDING을 돌려줬다. 오타 난 job_id도,
워커가 죽어 영원히 안 돌 작업도, 방금 큐에 들어간 작업도 모두 '대기 중...'이었다.
화면은 그 차이를 알 수 없어 영원히 폴링했다.
"""

import json
import time

import pytest
from fastapi.testclient import TestClient

from main import app
from routers import admin


class FakeRedis:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value

    def ping(self):
        return True


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(admin, "_get_redis_client", lambda: fake)
    return fake


def _status(client, job_id):
    r = client.get(f"/api/admin/evaluate/jobs/{job_id}")
    assert r.status_code == 200, r.text
    return r.json()


def test_unknown_job_is_not_found(client, fake_redis):
    """큐에 넣은 적 없는 job_id는 '대기 중'이 아니라 없는 것이다."""
    assert _status(client, "never-queued")["status"] == "NOT_FOUND"


def test_just_queued_job_is_pending(client, fake_redis):
    fake_redis.data[admin.job_registry_key("job-1")] = str(time.time())
    assert _status(client, "job-1")["status"] == "PENDING"


def test_queued_job_without_progress_goes_stale(client, fake_redis):
    """워커가 오래 집지 않으면 계속 '대기 중'으로 두지 않는다."""
    old = time.time() - (admin.JOB_STALE_AFTER_SECONDS + 10)
    fake_redis.data[admin.job_registry_key("job-2")] = str(old)
    body = _status(client, "job-2")
    assert body["status"] == "STALE"
    assert body.get("error")


def test_progress_is_reported_even_when_registry_is_gone(client, fake_redis):
    """결과 키가 있으면 대장이 만료됐어도 그대로 읽는다."""
    fake_redis.data["celery-task-meta-job-3"] = json.dumps(
        {"status": "PROGRESS", "result": {"current": 3, "total": 10, "percent": 30}}
    )
    body = _status(client, "job-3")
    assert body["status"] == "PROGRESS"
    assert body["progress"]["percent"] == 30


def test_success_is_reported(client, fake_redis):
    fake_redis.data["celery-task-meta-job-4"] = json.dumps(
        {"status": "SUCCESS", "result": {"total": 10, "success": 10, "failed": 0}}
    )
    body = _status(client, "job-4")
    assert body["status"] == "SUCCESS"
    assert body["result"]["success"] == 10


def test_queueing_registers_the_job(client, fake_redis, monkeypatch):
    """대장에 적어두지 않으면 방금 넣은 작업도 NOT_FOUND가 된다."""
    class FakeTask:
        id = "job-5"

    class FakeCelery:
        def send_task(self, *a, **k):
            return FakeTask()

    monkeypatch.setattr(admin, "_get_celery_app", lambda: FakeCelery())
    r = client.post("/api/admin/evaluate/bulk", json={"force_recalculate": False})
    assert r.status_code == 200, r.text
    assert r.json()["job_id"] == "job-5"
    assert fake_redis.data.get(admin.job_registry_key("job-5")) is not None
    assert _status(client, "job-5")["status"] == "PENDING"
