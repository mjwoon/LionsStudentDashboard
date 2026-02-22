import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.begin() as conn:
        try:
            conn.execute(text('ALTER TABLE student_courses DROP CONSTRAINT IF EXISTS student_courses_course_id_fkey CASCADE'))
        except Exception as e:
            print(f"Ignore drop constraint error: {e}")
            
        try:
            conn.execute(text('ALTER TABLE student_courses DROP COLUMN IF EXISTS course_id CASCADE'))
        except Exception as e:
            print(f"Ignore drop column error: {e}")
            
        try:
            conn.execute(text('ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS course_code VARCHAR(20)'))
            conn.execute(text('ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS course_name VARCHAR(100)'))
            conn.execute(text('ALTER TABLE student_courses ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 3'))
        except Exception as e:
            print(f"Ignore add column error: {e}")
    print("Migration successful.")
