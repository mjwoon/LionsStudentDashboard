import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Base, College, Department

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/my_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_departments():
    db = SessionLocal()
    
    # Create computing college
    computing = db.query(College).filter(College.name == "컴퓨팅대학").first()
    if not computing:
        computing = College(name="컴퓨팅대학")
        db.add(computing)
        db.commit()
        db.refresh(computing)
    
    cse = db.query(Department).filter(Department.code == "CSE").first()
    if not cse:
        cse = Department(code="CSE", name="컴퓨터학부", college_id=computing.id)
        db.add(cse)
        db.commit()
    
    print("Seeded College and Department (CSE) successfully.")
    
if __name__ == "__main__":
    seed_departments()
