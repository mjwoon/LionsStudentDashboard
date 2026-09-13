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


# ── 돌기 시작한 뒤에 멈춘 작업 ──────────────────────────────────────
# NOT_FOUND/STALE은 '큐에 들어갔는데 워커가 안 집는' 경우만 잡았다. 돌다가 죽거나
# 진행률 기록이 끊기면 PROGRESS인 채로 남아 화면이 영원히 폴링한다. 서버가 진행률이
# 언제 마지막으로 움직였는지 재서 가른다.

def _progress_meta(current, total=12000):
    return json.dumps({
        "status": "PROGRESS",
        "result": {"current": current, "total": total,
                   "percent": round(current / total * 100, 1),
                   "status": "평가 중...", "success_count": current, "error_count": 0},
    })


def test_advancing_progress_is_reported(client, fake_redis):
    fake_redis.data["celery-task-meta-job-a"] = _progress_meta(100)
    assert _status(client, "job-a")["status"] == "PROGRESS"
    fake_redis.data["celery-task-meta-job-a"] = _progress_meta(200)
    assert _status(client, "job-a")["status"] == "PROGRESS"


def test_frozen_progress_goes_stale(client, fake_redis):
    """같은 current가 오래 유지되면 진행이 멈춘 것이다."""
    fake_redis.data["celery-task-meta-job-b"] = _progress_meta(3080)
    assert _status(client, "job-b")["status"] == "PROGRESS"      # 첫 관측 — 기준점을 잡는다

    # 기준점을 임계값 이전으로 되돌린다(시간 경과를 흉내).
    snap = fake_redis.data[admin.progress_snapshot_key("job-b")]
    current, ts = snap.split(":")
    fake_redis.data[admin.progress_snapshot_key("job-b")] = (
        f"{current}:{float(ts) - admin.JOB_STALE_AFTER_SECONDS - 10}"
    )

    body = _status(client, "job-b")
    assert body["status"] == "STALE"
    assert body.get("error")
    # 어디서 멈췄는지 화면이 보여줄 수 있어야 한다.
    assert body["progress"]["current"] == 3080


def test_progress_that_moves_again_resets_the_clock(client, fake_redis):
    fake_redis.data["celery-task-meta-job-c"] = _progress_meta(100)
    _status(client, "job-c")
    snap = fake_redis.data[admin.progress_snapshot_key("job-c")]
    current, ts = snap.split(":")
    fake_redis.data[admin.progress_snapshot_key("job-c")] = (
        f"{current}:{float(ts) - admin.JOB_STALE_AFTER_SECONDS - 10}"
    )
    # 그 사이 워커가 다시 움직였다
    fake_redis.data["celery-task-meta-job-c"] = _progress_meta(300)
    assert _status(client, "job-c")["status"] == "PROGRESS"


def test_success_is_not_affected_by_staleness(client, fake_redis):
    fake_redis.data["celery-task-meta-job-d"] = json.dumps(
        {"status": "SUCCESS", "result": {"total": 10, "success": 10, "failed": 0}}
    )
    assert _status(client, "job-d")["status"] == "SUCCESS"
