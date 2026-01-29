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
    track = Column(String(20), nullable=True)  # 전계열, 자연계열, 인문사회계열
    pride = Column(String(10))  # L, I, O, N, S, E
    class_number = Column(Integer)  # 분반
    status = Column(String(20), default="재학")  # 재학, 휴학, 졸업 등
    
    # GPA 캐시 (성능 최적화 - 매번 계산하지 않고 업데이트 시 갱신)
    current_gpa = Column(Numeric(3, 2), nullable=True)  # 현재 평점 (4.5 만점)
    total_credits = Column(Integer, default=0)  # 총 이수 학점
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    department = relationship("Department", back_populates="students")
    advisor = relationship("Advisor", back_populates="students")
    course_enrollments = relationship("CourseEnrollment", back_populates="student")
    surveys = relationship("MajorSurvey", back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    course_type = Column(String(50))  # 전공기초, 전공필수, 전공선택, 교양필수 등
    department_id = Column(Integer, ForeignKey("departments.id"))
    course_year = Column(Integer, nullable=True)  # 권장 학년: 1, 2, 3, 4
    semester = Column(Integer, nullable=True)  # 1 or 2
    is_retake_only = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    department = relationship("Department", back_populates="courses")
    enrollments = relationship("CourseEnrollment", back_populates="course")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)  # 1 or 2
    completion_type = Column(String(50))  # 이수구분: 전공필수, 전공선택 등
    is_retake = Column(Boolean, default=False)
    grade = Column(String(5), nullable=True)  # A+, A0, B+, B0, F 등
    numeric_grade = Column(Numeric(3, 2), nullable=True)  # 4.5, 4.0, 3.0 등 계산용
    created_at = Column(DateTime, default=datetime.utcnow)
    
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


class DecisionStatus(Base):
    """결정 상태 코드 테이블 (최종결정, 고민중 등)"""
    __tablename__ = "decision_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status_name = Column(String(50), nullable=False, unique=True)
    
    surveys = relationship("MajorSurvey", back_populates="decision_status")


class MajorSurvey(Base):
    __tablename__ = "major_surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    round_id = Column(Integer, ForeignKey("survey_rounds.id"))
    first_choice_dept_id = Column(Integer, ForeignKey("departments.id"))
    second_choice_dept_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    decision_status_id = Column(Integer, ForeignKey("decision_statuses.id"), nullable=True)
    decision_scale = Column(Integer)  # 리커트 척도 1~5
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="surveys")
    survey_round = relationship("SurveyRound", back_populates="surveys")
    first_choice = relationship("Department", foreign_keys=[first_choice_dept_id])
    second_choice = relationship("Department", foreign_keys=[second_choice_dept_id])
    decision_status = relationship("DecisionStatus", back_populates="surveys")


class DepartmentEntryRequirement(Base):
    """학과별 진입 요건 정의 (학년도별/그룹별)"""
    __tablename__ = "department_entry_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    admission_year = Column(Integer, nullable=False)  # 적용 학번 (2024, 2025 등)
    requirement_group = Column(Integer, nullable=False)  # 1번 그룹(필수과목군), 2번 그룹 등
    target_grade_level = Column(Enum(GradeLevelEnum), nullable=False)  # 기준 성적: A, B, C
    required_count = Column(Integer, nullable=False)  # 필요한 과목 수
    requirement_text = Column(Text, nullable=False)  # 사용자 노출용 설명
    is_alert_required = Column(Boolean, default=False)  # 학생설계전공 등 알림창 여부
    
    # OR 조건 처리를 위한 필드
    # 같은 requirement_group 내에서 여러 조건이 있을 때 OR로 평가
    # 예: "B 이상 2과목 OR A 이상 1과목" → 두 개의 레코드를 같은 그룹에 넣고 logic_operator="OR"
    logic_operator = Column(String(10), default="AND")  # "AND" 또는 "OR"
    
    department = relationship("Department")
    requirement_courses = relationship("RequirementCourse", back_populates="requirement", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'admission_year', 'requirement_group', name='uq_dept_year_group'),
    )


class RequirementCourse(Base):
    """요건 대상 과목 매핑"""
    __tablename__ = "requirement_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("department_entry_requirements.id", ondelete="CASCADE"), nullable=False)
    course_code = Column(String(20), ForeignKey("courses.course_code"), nullable=False)
    
    requirement = relationship("DepartmentEntryRequirement", back_populates="requirement_courses")
    course = relationship("Course")


class StudentRequirementStatus(Base):
    """학생별 진단 결과 캐시 테이블 (성능 최적화 및 AI 총평)"""
    __tablename__ = "student_requirement_status"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    is_satisfied = Column(Boolean, default=False)  # 최종 충족 여부
    
    # 진단 상세 데이터 (JSON)
    # 예: {"completed": 2, "required": 2, "details": [{"code": "MAT101", "grade": "A0"}]}
    analysis_json = Column(JSON, nullable=True)
    
    # 세부 평가 점수 (2-메트릭 평가 체계)
    curriculum_completion_score = Column(Numeric(5, 2), nullable=True)  # 1학년 전공체계도 완성도 점수 (0-100)
    related_courses_score = Column(Numeric(5, 2), nullable=True)  # 유사과목 점수 (0-100)
    overall_score = Column(Numeric(5, 2), nullable=True)  # 종합 점수 (가중 평균, 0-100)
    
    ai_summary = Column(Text, nullable=True)  # LLM이 생성한 맞춤형 커멘트
    calculated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = relationship("Student")
    department = relationship("Department")
    
    __table_args__ = (
        UniqueConstraint('student_id', 'department_id', name='uq_student_dept_eval'),
    )
