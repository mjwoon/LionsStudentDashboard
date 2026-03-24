"""
Celery 앱 설정
Redis를 broker/backend로 사용합니다.
"""

import os
import ssl
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"]
)

# Celery 설정
celery_app.conf.update(
    # 결과 만료 시간 (24시간)
    result_expires=86400,
    # 태스크 직렬화
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 타임존
    timezone="Asia/Seoul",
    enable_utc=True,
    # Worker 설정
    worker_prefetch_multiplier=1,  # 한 번에 하나씩 처리
    task_acks_late=True,           # 완료 후 ACK (안정성)
    # 진행상황 추적
    task_track_started=True,
)

# rediss:// (TLS) 사용 시 SSL 설정 추가 (Upstash 등)
if REDIS_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {'ssl_cert_reqs': ssl.CERT_NONE}
    celery_app.conf.redis_backend_use_ssl = {'ssl_cert_reqs': ssl.CERT_NONE}
