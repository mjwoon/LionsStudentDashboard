from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from config import settings

# Database URL - PostgreSQL (postgres:// / postgresql:// 는 psycopg3용으로 정규화됨)
DATABASE_URL = settings.normalized_database_url

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=settings.db_echo  # DB_ECHO 환경변수로 제어 (기본 False)
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to initialize database
def init_db():
    from models.models import Base
    Base.metadata.create_all(bind=engine)
