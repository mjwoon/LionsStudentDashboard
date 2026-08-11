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

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 개발 편의용 기본값이자 '운영에 있으면 안 되는' 값들의 목록
_INSECURE_NEO4J_PASSWORD = "password123"


class Settings(BaseSettings):
    # 실행 환경: development | production (운영에서 개발용 시크릿 사용을 차단)
    app_env: str = "development"

    # --- Database (PostgreSQL) ---
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/my_db"
    db_echo: bool = False  # 기존 database.py는 echo=True 상시 활성이었음(운영 소음) → env로 제어

    # --- Neo4j Graph DB ---
    neo4j_uri: str = "bolt://localhost:7687"
    # NEO4J_USER 우선, 없으면 NEO4J_USERNAME 폴백(.env는 후자를 씀). graphDB/backend/.env
    # 간 사용자명 키 불일치로 로컬 연결이 기본값으로 떨어지던 문제를 해소.
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("NEO4J_USER", "NEO4J_USERNAME"),
    )
    neo4j_password: str = "password123"  # dev-only; 운영은 env로 override (위 주의 참조)

    # --- Redis / Celery broker ---
    redis_url: str = "redis://redis:6379/0"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def _forbid_dev_secrets_in_production(self):
        if self.app_env.lower() == "production" and self.neo4j_password == _INSECURE_NEO4J_PASSWORD:
            raise ValueError(
                "APP_ENV=production인데 개발용 기본 NEO4J_PASSWORD가 사용되고 있습니다. "
                "NEO4J_PASSWORD 환경변수를 실제 값으로 설정하세요."
            )
        return self

    @cached_property
    def cors_origin_list(self) -> list[str]:
        # CORS_ORIGINS(env, 운영 프론트 주소) + 로컬 개발 오리진을 항상 병합 허용.
        # 배포 백엔드에 로컬 프론트(localhost:5173/3000)가 붙어도 CORS 차단되지 않도록 함.
        # (브라우저는 Origin을 위조할 수 없어 localhost 허용은 안전)
        configured = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        dev_origins = ["http://localhost:5173", "http://localhost:3000"]
        return list(dict.fromkeys(configured + dev_origins))  # 순서 유지 + 중복 제거

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
