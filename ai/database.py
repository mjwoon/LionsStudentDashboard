"""
AI Worker용 데이터베이스 연결
Backend와 동일한 PostgreSQL DB에 접속합니다.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/my_db")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # 연결 상태 확인
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """DB 세션 컨텍스트 매니저 (Celery 태스크용)"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
