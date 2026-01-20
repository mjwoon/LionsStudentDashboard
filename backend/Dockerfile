# 1. uv가 설치된 공식 이미지를 베이스로 사용 (빌드 속도가 매우 빠름)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 환경 변수 설정 (Python이 .pyc 파일을 생성하지 않도록 하고 버퍼링을 끎)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 4. 의존성 파일 복사 (캐싱을 위해 먼저 복사)
# 로컬에서 `uv init`을 실행해 생성된 파일들입니다.
COPY pyproject.toml uv.lock ./

# 5. 의존성 설치 (가상환경 없이 시스템에 직접 설치하여 이미지 크기 최적화)
RUN uv sync --frozen --no-cache

# 6. 소스 코드 복사
COPY . .

# 7. FastAPI 실행
# seed_data.py가 자동으로 DB 연결을 기다림
CMD ["sh", "-c", "uv run python seed_data.py && uv run fastapi dev main.py --host 0.0.0.0 --port 8080"]