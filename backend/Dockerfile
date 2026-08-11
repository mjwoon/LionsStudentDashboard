# Backend (FastAPI) — uv workspace 빌드
# 빌드 컨텍스트: 저장소 루트 (.)  ← docker-compose / render.yaml에서 context: . 로 설정
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_HTTP_TIMEOUT=600

# 워크스페이스 메타 + lions-core 전체 소스(editable 멤버라 빌드 시 README/소스 필요) + backend 매니페스트
COPY pyproject.toml uv.lock ./
COPY packages/lions-core/ packages/lions-core/
COPY backend/pyproject.toml backend/
RUN uv sync --frozen --no-dev --package backend

# backend 소스
COPY backend/ backend/

WORKDIR /app/backend
# 운영 스키마는 Alembic(release preDeploy)이 담당. create_all은 APP_ENV로 게이트됨.
CMD ["uv", "run", "--package", "backend", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
