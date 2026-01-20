from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class College(Base):
    __tablename__ = "colleges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    
    departments = relationship("Department", back_populates="college")


class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id"))
    min_credits = Column(Integer, default=130)
    homepage_url = Column(String(255), nullable=True)
    
    college = relationship("College", back_populates="departments")
    students = relationship("Student", back_populates="department")
    courses = relationship("Course", back_populates="department")
    advisors = relationship("Advisor", back_populates="department")


class Advisor(Base):
    __tablename__ = "advisors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    
    department = relationship("Department", back_populates="advisors")
    students = relationship("Student", back_populates="advisor")


class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    department_id = Column(Integer, ForeignKey("departments.id"))
    advisor_id = Column(Integer, ForeignKey("advisors.id"), nullable=True)
    pride = Column(String(10))  # L, I, O, N, S, E
    class_number = Column(Integer)  # 분반
    status = Column(String(20), default="재학")  # 재학, 휴학, 졸업 등
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    department = relationship("Department", back_populates="students")
    advisor = relationship("Advisor", back_populates="students")
    course_enrollments = relationship("CourseEnrollment", back_populates="student")
    surveys = relationship("MajorSurvey", back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(20), unique=True, nullable=False)
    course_name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    course_type = Column(String(50))  # 전공필수, 전공선택, 교양필수 등
    department_id = Column(Integer, ForeignKey("departments.id"))
    is_entry_requirement = Column(Boolean, default=False)
    is_recommended = Column(Boolean, default=False)
    is_retake_only = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    
    department = relationship("Department", back_populates="courses")
    enrollments = relationship("CourseEnrollment", back_populates="course")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)  # 1 or 2
    completion_type = Column(String(50))  # 전공필수, 전공선택 등
    is_retake = Column(Boolean, default=False)
    grade = Column(String(5), nullable=True)  # A+, A, B+ 등
    
    student = relationship("Student", back_populates="course_enrollments")
    course = relationship("Course", back_populates="enrollments")


class SurveyRound(Base):
    __tablename__ = "survey_rounds"
    
    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer, nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    surveys = relationship("MajorSurvey", back_populates="survey_round")


class MajorSurvey(Base):
    __tablename__ = "major_surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    round_id = Column(Integer, ForeignKey("survey_rounds.id"))
    first_choice_dept_id = Column(Integer, ForeignKey("departments.id"))
    second_choice_dept_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    decision_scale = Column(Integer)  # 1~5
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="surveys")
    survey_round = relationship("SurveyRound", back_populates="surveys")
    first_choice = relationship("Department", foreign_keys=[first_choice_dept_id])
    second_choice = relationship("Department", foreign_keys=[second_choice_dept_id])
