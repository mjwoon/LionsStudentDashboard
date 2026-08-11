from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from lions_core.config import settings

# Database URL - PostgreSQL (postgres:// / postgresql:// 는 psycopg3용으로 정규화됨)
DATABASE_URL = settings.normalized_database_url

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=settings.db_echo  # DB_ECHO 환경변수로 제어 (기본 False)
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get DB session (FastAPI)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Context manager for standalone (non-FastAPI) usage, e.g. Celery worker
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to initialize database
def init_db():
    """개발 편의용 스키마 생성.

    운영에서는 create_all 대신 Alembic 마이그레이션(`alembic upgrade head`)을 사용한다.
    두 경로 모두 동일한 Base.metadata에서 파생되므로 스키마는 일치한다.
    """
    from lions_core.models import Base
    Base.metadata.create_all(bind=engine)
