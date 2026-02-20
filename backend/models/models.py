from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON, UniqueConstraint, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class GradeLevelEnum(enum.Enum):
    """진입요건 기준 성적 등급"""
    A = "A"
    B = "B"
    C = "C"


class College(Base):
    __tablename__ = "colleges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    
    departments = relationship("Department", back_populates="college")


class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    college_id = Column(Integer, ForeignKey("colleges.id"))
    min_credits = Column(Integer, default=130)
    
    college = relationship("College", back_populates="departments")
    students = relationship("Student", back_populates="department")
    courses = relationship("Course", back_populates="department")
    advisors = relationship("Advisor", back_populates="department")


class Advisor(Base):
    __tablename__ = "advisors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100))
    department_id = Column(Integer, ForeignKey("departments.id"))
    
    department = relationship("Department", back_populates="advisors")
    students = relationship("Student", back_populates="advisor")


class Student(Base):
    __tablename__ = "students"
    
    student_id = Column(String(10), primary_key=True)  # 학번 (PK)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    advisor_id = Column(Integer, ForeignKey("advisors.id"), nullable=True)
    pride = Column(String(10))  # LIONSE 등급 등
    class_number = Column(Integer)  # 분반
    
    # 기존 유지 필드 (updated_database.md에는 없지만 기능 유지를 위해 보존)
    track = Column(String(20), nullable=True)  # 전계열, 자연계열, 인문사회계열
    status = Column(String(20), default="재학")  # 재학, 휴학, 졸업 등
    current_gpa = Column(Numeric(3, 2), nullable=True)  # 현재 평점 (4.5 만점)
    total_credits = Column(Integer, default=0)  # 총 이수 학점
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    department = relationship("Department", back_populates="students")
    advisor = relationship("Advisor", back_populates="students")
    course_enrollments = relationship("StudentCourse", back_populates="student")
    surveys = relationship("MajorSurvey", back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    
    course_id = Column(Integer, primary_key=True, index=True)  # PK renamed from 'id'
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    course_type = Column(String(30))  # 전공기초, 전공필수 등
    course_department = Column(Integer, ForeignKey("departments.id"))  # 관장학과
    course_year = Column(Integer, nullable=False)  # 권장 학년
    semester = Column(Integer, nullable=False)  # 권장 학기
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 기존 유지 필드
    is_retake_only = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    
    department = relationship("Department", back_populates="courses",
                              foreign_keys=[course_department])
    enrollments = relationship("StudentCourse", back_populates="course")


class StudentCourse(Base):
    """학생 수강과목 테이블 (기존 CourseEnrollment에서 renamed)"""
    __tablename__ = "student_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(10), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False)
    grade = Column(String(5), nullable=False)  # A+, B0, F 등
    numeric_grade = Column(Numeric(3, 2))  # 4.5, 3.0 등 계산용 점수
    
    year = Column(Integer, nullable=False)  # 수강 연도
    semester = Column(Integer, nullable=False)  # 수강 학기
    
    completion_type = Column(String(20), nullable=False)  # 이수구분 (수강생 기준)
    is_retake = Column(Boolean, default=False)  # 재수강 여부
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="course_enrollments")
    course = relationship("Course", back_populates="enrollments")


class SurveyRound(Base):
    __tablename__ = "survey_rounds"
    
    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED 등
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    surveys = relationship("MajorSurvey", back_populates="survey_round")


class DecisionStatus(Base):
    """결정 상태 코드 테이블 (최종결정, 고민중 등)"""
    __tablename__ = "decision_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status_name = Column(String(50), nullable=False)
    
    surveys = relationship("MajorSurvey", back_populates="decision_status")


class MajorSurvey(Base):
    __tablename__ = "major_surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(10), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    
    survey_round_id = Column(Integer, ForeignKey("survey_rounds.id"), nullable=False)  # renamed from round_id
    first_choice_id = Column(Integer, ForeignKey("departments.id"), nullable=False)  # renamed from first_choice_dept_id
    second_choice_id = Column(Integer, ForeignKey("departments.id"), nullable=False)  # renamed from second_choice_dept_id
    
    decision_status_id = Column(Integer, ForeignKey("decision_statuses.id"), nullable=True)
    decision_scale = Column(Integer)  # 리커트 척도 (1~5)
    
    survey_date = Column(DateTime, default=datetime.utcnow)  # renamed from submitted_at
    
    student = relationship("Student", back_populates="surveys")
    survey_round = relationship("SurveyRound", back_populates="surveys")
    first_choice = relationship("Department", foreign_keys=[first_choice_id])
    second_choice = relationship("Department", foreign_keys=[second_choice_id])
    decision_status = relationship("DecisionStatus", back_populates="surveys")


class DepartmentEntryRequirement(Base):
    """학과별 진입 요건 정의 (학년도별/그룹별)"""
    __tablename__ = "department_entry_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    
    admission_year = Column(Integer, nullable=False)  # 적용 학번 (2026 등)
    requirement_group = Column(Integer, nullable=False)  # 1번 그룹(필수과목군) 등
    
    target_grade_level = Column(Enum(GradeLevelEnum), nullable=False)  # 기준 성적: A, B, C
    required_count = Column(Integer, nullable=False)  # 필요한 과목 수
    requirement_text = Column(Text, nullable=False)  # 사용자 노출용 설명
    is_alert_required = Column(Boolean, default=False)  # 설계전공 등 알림창 여부
    
    # 기존 유지 필드
    logic_operator = Column(String(10), default="AND")  # "AND" 또는 "OR"
    
    department = relationship("Department")
    requirement_courses = relationship("RequirementCourse", back_populates="requirement", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'admission_year', 'requirement_group', name='uq_dept_year_group'),
    )


class RequirementCourse(Base):
    """요건 대상 과목 매핑 (course_id FK 참조)"""
    __tablename__ = "requirement_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("department_entry_requirements.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False)  # changed from course_code to FK
    
    requirement = relationship("DepartmentEntryRequirement", back_populates="requirement_courses")
    course = relationship("Course")  # new relationship


class StudentRequirementStatus(Base):
    """학생별 진단 결과 캐시 테이블 (성능 최적화 및 AI 총평)"""
    __tablename__ = "student_requirement_status"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(10), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    is_satisfied = Column(Boolean, default=False)  # 최종 충족 여부
    
    # 진단 상세 데이터 (JSON)
    analysis_json = Column(JSON, nullable=True)
    
    # 기존 유지: 세부 평가 점수
    curriculum_completion_score = Column(Numeric(5, 2), nullable=True)
    related_courses_score = Column(Numeric(5, 2), nullable=True)
    overall_score = Column(Numeric(5, 2), nullable=True)
    
    ai_summary = Column(Text, nullable=True)  # LLM이 생성한 맞춤형 커멘트
    calculated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = relationship("Student")
    department = relationship("Department")
    
    __table_args__ = (
        UniqueConstraint('student_id', 'department_id', name='uq_student_dept_eval'),
    )


class Curriculum(Base):
    """학과별 교육과정 지정 데이터 (유지)"""
    __tablename__ = "curriculums"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    course_year = Column(Integer, nullable=False)  # 1, 2, 3, 4학년
    course_code = Column(String(20), nullable=False)
    course_name = Column(String(100), nullable=False)
    
    department = relationship("Department")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'course_code', name='uq_curriculum_dept_course'),
    )


class CourseRecommendation(Base):
    """학과별 권장과목 데이터 (유지)"""
    __tablename__ = "course_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    course_name = Column(String(100), nullable=False)
    
    department = relationship("Department")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'course_name', name='uq_recommendation_dept_course'),
    )
