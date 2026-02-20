# uv가 설치된 공식 이미지 사용
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 의존성 설치
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-cache 2>/dev/null || uv sync --no-cache

# 소스 코드 복사
COPY . .

# Celery Worker 실행
CMD ["uv", "run", "celery", "-A", "celery_app", "worker", "--loglevel=info", "--concurrency=2"]
