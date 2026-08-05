"""
중앙 설정(Single Source of Truth).

기존에 main.py / database.py / graph_service.py / routers/admin.py 에 흩어져 있던
os.getenv 호출을 한 곳으로 모은다. 현재 동작을 보존하기 위해 프로세스 환경변수만
읽으며(.env 자동 로드 없음), 환경변수 이름과 기본값은 기존과 동일하게 유지한다.

주의(follow-up): neo4j_password 의 개발용 기본값('password123')은 docker-compose.yml
에도 동일하게 존재한다. 완전한 시크릿 제거(운영 시 미설정이면 즉시 실패 + compose 정리)
는 로컬 개발 동작을 깨지 않기 위해 별도 작업으로 분리한다.
"""

from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database (PostgreSQL) ---
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/my_db"
    db_echo: bool = False  # 기존 database.py는 echo=True 상시 활성이었음(운영 소음) → env로 제어

    # --- Neo4j Graph DB ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"  # dev-only; 운영은 env로 override (위 주의 참조)

    # --- Redis / Celery broker ---
    redis_url: str = "redis://redis:6379/0"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @cached_property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @cached_property
    def normalized_database_url(self) -> str:
        """Render 등은 postgres:// 또는 postgresql:// 로 주므로 psycopg3 드라이버용으로 변환."""
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
