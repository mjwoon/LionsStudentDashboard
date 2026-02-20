"""
Celery 앱 설정
Redis를 broker/backend로 사용합니다.
"""

import os
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
