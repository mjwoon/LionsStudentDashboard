from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Database URL - SQLite for development, can be changed to PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lions_dashboard.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=True  # Set to False in production
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
    from models.database import Base
    Base.metadata.create_all(bind=engine)
