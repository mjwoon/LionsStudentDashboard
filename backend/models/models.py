from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON, UniqueConstraint, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class GradeLevelEnum(enum.Enum):
    """
    진입요건(예: 전공 필수과목 등) 통과의 기준이 되는 성적 등급을 정의하는 열거형(Enum)입니다.

    Attributes:
        A: A 등급 수준 (A0 이상 등)
        B: B 등급 수준 (B0 이상 등)
        C: C 등급 수준
    """
    A = "A"
    B = "B"
    C = "C"


class College(Base):
    """
    단과대학 기본 정보를 저장하는 데이터베이스 모델입니다.

    Attributes:
        id (Integer): 단과대학 고유 다중 식별자 (PK)
        name (String): 단과대학 명칭 (예: 소프트웨어융합대학 등, Unique)
        
        departments (relationship): 이 단과대학에 소속된 학과(Department) 목록 (1:N 관계)
    """
    __tablename__ = "colleges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    
    departments = relationship("Department", back_populates="college")


class Department(Base):
    """
    학과 및 전공 단위를 저장하는 데이터베이스 모델입니다.

    Attributes:
        id (Integer): 학과의 고유 식별자 (PK)
        code (String): 학과/전공 코드 기호 (예: CS, AI 등, Unique)
        name (String): 학과 명칭 (예: 컴퓨터공학과, Unique)
        college_id (Integer): 소속 단과대학의 참조 ID (FK)
        min_credits (Integer): 최소 졸업/이수 요구 학점 (기본값: 130)
        
        college (relationship): 소속 단과대학 객체 (N:1 관계)
        students (relationship): 등록된 소속 학생 목록 (1:N 관계)
        courses (relationship): 이 학과에서 개설/관장하는 교과목 목록 (1:N 관계)
        advisors (relationship): 학과에 소속된 지도교수진 목록 (1:N 관계)
    """
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
    """
    학생들을 관리하는 지도교수 정보를 저장하는 모델입니다.

    Attributes:
        id (Integer): 교수의 고유 식별자 (PK)
        name (String): 지도교수 성명
        email (String): 연락 이메일 주소
        department_id (Integer): 소속 학과 단일 참조 ID (FK)
        
        department (relationship): 교수가 속한 학과 (N:1)
        students (relationship): 이 교수에게 배정된 학생 목록 (1:N)
    """
    __tablename__ = "advisors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100))
    department_id = Column(Integer, ForeignKey("departments.id"))
    
    department = relationship("Department", back_populates="advisors")
    students = relationship("Student", back_populates="advisor")


class Student(Base):
    """
    학생의 학적 및 기본 이력을 관리하는 데이터베이스 모델입니다.

    Attributes:
        student_id (Integer): 학생 고유 학번 번호 (PK)
        name (String): 학생 실명
        email (String): 연락/계정 이메일
        phone (String): 연락 가능한 휴대폰 번호
        department_id (Integer): 원 소속 등록 학과의 ID (FK)
        advisor_id (Integer): 배정된 단일 지도교수의 식별 ID (FK)
        pride (String): 학생 배정 PRIDE/LIONSE 등급
        class_number (Integer): 분반 단위 숫자
        track (String): 배정 트랙 혹은 입학계열 (예: 자연계열 등)
        status (String): 현재 학적 상태 (기본값: "재학")
        current_gpa (Numeric): 취득 종합 현재 평점
        total_credits (Integer): 누적 취득 학점
        updated_at (DateTime): 학적 정보의 마지막 최종 수정 일시
        
        department (relationship): 해당 학생의 원 소속 학과 (N:1)
        advisor (relationship): 이 학생의 매핑 지도교수 (N:1)
        course_enrollments (relationship): 학생이 수강한 과목 성적 이력 (1:N)
        surveys (relationship): 학생이 응답한 진로/희망전공 설문 내역 (1:N)
    """
    __tablename__ = "students"
    
    student_id = Column(Integer, primary_key=True)  # 학번 (PK)
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
    """
    전체 교육과정에 개설되는 개별 교과목 정보를 다루는 모델입니다.

    Attributes:
        course_id (Integer): 과목 데이터의 고유 식별 레코드 ID (PK)
        course_code (String): 교내 학수번호 / 고유 과목코드 (Unique)
        course_name (String): 과목의 이름
        credits (Integer): 취득 시 인정 받는 학점 크기
        course_type (String): 이수 구분 체계 (예: 전필, 교필, 전선 등)
        course_department (String): 과목의 개설·관장을 주도하는 주관 학과명 참조 외래키 (FK)
        course_year (Integer): 이수를 권장하는 추천 학년
        semester (Integer): 개설·권장 수강 추천 학기
        created_at (DateTime): 해당 과목 데이터의 등록 기준 시점
        is_retake_only (Boolean): 오직 재수강생만 수강 가능한 전용 과목인지 체크
        description (Text): 과목 개요 데이터나 실라버스 정보 등
        
        department (relationship): 해당 과목을 주관하는 학과 정보 객체 (N:1)
    """
    __tablename__ = "courses"
    
    course_id = Column(Integer, primary_key=True, index=True)  # PK renamed from 'id'
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    course_type = Column(String(30))  # 전공기초, 전공필수 등
    course_department = Column(String(20), ForeignKey("departments.name"))  # 관장학과
    course_year = Column(Integer, nullable=False)  # 권장 학년
    semester = Column(Integer, nullable=False)  # 권장 학기
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 기존 유지 필드
    is_retake_only = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    
    department = relationship("Department", back_populates="courses",
                              foreign_keys=[course_department])


class StudentCourse(Base):
    """
    특정 학생이 한 학기에 수강을 완료하여 취득한 성적(수강내역)을 매핑하는 모델입니다.

    Attributes:
        id (Integer): 수강이력 레코드 식별자 (PK)
        student_id (Integer): 수강생의 고유 학번 참조 (FK, CASCADE 삭제 적용)
        course_code (String): 수강한 교과목의 학수번호
        course_name (String): 수강 과목의 명칭
        credits (Integer): 이수 학점수 확인용 (기본값: 3)
        grade (String): 받은 취득 성적 기호 표기 (예: A+, F 등)
        numeric_grade (Numeric): GPA 등의 연산에 직접 활용하는 숫자화된 평점
        year (Integer): 실제 강의 이수 년도
        semester (Integer): 실제 강의 이수 학기
        completion_type (String): 학생 개개인의 입장에서 인정되는 이수 타입구분 기호(전선, 기필 등)
        is_retake (Boolean): 재수강 인정 여부 플래그
        created_at (DateTime): 이력 등록 시점
        
        student (relationship): 이 강의를 수강한 학생 객체정보 (N:1)
    """
    __tablename__ = "student_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    
    course_code = Column(String(20), nullable=False)
    course_name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False, default=3)
    
    grade = Column(String(5), nullable=False)  # A+, B0, F 등
    numeric_grade = Column(Numeric(3, 2))  # 4.5, 3.0 등 계산용 점수
    
    year = Column(Integer, nullable=False)  # 수강 연도
    semester = Column(Integer, nullable=False)  # 수강 학기
    
    completion_type = Column(String(20), nullable=False)  # 이수구분 (수강생 기준)
    is_retake = Column(Boolean, default=False)  # 재수강 여부
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="course_enrollments")


class SurveyRound(Base):
    """
    희망전공 등 학생 설문조사 진행 회차 단위 마스터 데이터를 저장하는 모델입니다.

    Attributes:
        id (Integer): 설문 회차 식별자 (PK)
        round_number (Integer): 설문조사 회차 순번
        title (String): 표시되는 설문 테마/제목 (예: "4차 전공 수요 조사")
        status (String): 진행 상태 ("OPEN" 등)
        start_date (DateTime): 설문 집계 시작 시점
        end_date (DateTime): 설문 마감/종료 시점
        
        surveys (relationship): 이 회차에 소속되어 수집된 모든 개별 설문 응답(MajorSurvey) 목록 (1:N)
    """
    __tablename__ = "survey_rounds"
    
    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED 등
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    surveys = relationship("MajorSurvey", back_populates="survey_round")


class DecisionStatus(Base):
    """
    학생의 전공 선택/결정 단계나 상태(예: 확정, 고민중, 미정 등)를 공통 코드로 관리하는 모델입니다.

    Attributes:
        id (Integer): 결정 상태 코드 식별자 (PK)
        status_name (String): 상태 식별 명칭 표기 문자
        
        surveys (relationship): 이 상태값과 연결되어 있는 설문 응답 목록 (1:N)
    """
    __tablename__ = "decision_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status_name = Column(String(50), nullable=False)
    
    surveys = relationship("MajorSurvey", back_populates="decision_status")


class MajorSurvey(Base):
    """
    개별 학생 단원별 희망/지망 전공 설문 이력을 저장하는 트랜잭션 모델입니다.

    Attributes:
        id (Integer): 하나의 제출된 설문 건 데이터 ID (PK)
        student_id (Integer): 설문에 참여/작성한 학생의 학번 (FK)
        survey_round_id (Integer): 이 설문 제출 건이 소속된 회차 ID (FK)
        first_choice_id (Integer): 1순위로 지망하고 싶은 학과의 ID (FK)
        second_choice_id (Integer): 2순위로 지망(고려)하는 학과의 ID (FK)
        decision_status_id (Integer): 전공을 결정한 상태 징후를 나타내는 참조 ID (FK)
        decision_scale (Integer): 진로결정 확인도 혹은 리커트 척도 (보통 1~5점)
        survey_date (DateTime): 응답을 제출하거나 시스템에 등록한 시각
        
        student (relationship): 작성자 학생 정보 객체 (N:1)
        survey_round (relationship): 속한 회차 기본 정보 (N:1)
        first_choice (relationship): 지정된 1지망 학과 객체 (N:1)
        second_choice (relationship): 지정된 2지망 학과 객체 (N:1)
        decision_status (relationship): 선택된 결정 상태 상세 정보 (N:1)
    """
    __tablename__ = "major_surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    
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
    """
    특정 학과에 진입하기 위해 충족해야 되는 여러 조건군(요구과목 집합 등) 데이터를 관리하는 모델입니다.

    Attributes:
        id (Integer): 진입 요건 그룹 정의 식별자 (PK)
        department_id (Integer): 요건을 강제하는 주체 학과 ID (FK)
        admission_year (Integer): 이 요건 룰셋이 적용 시작/유효해지는 입학년도(예컨대 2026학번부터)
        requirement_group (Integer): 여러 조건을 병합 판정하기 위해 분류되는 그룹 Index
        target_grade_level (Enum): 취득 성적이 어느 기준이어야 통과하는지 (A, B, C 등)
        required_count (Integer): 그룹에 소속된 과목 중 반드시 수강/통과해야하는 최소한의 갯수
        requirement_text (String): 관리자나 일반 학생에게 전시되는 텍스트적 안내 문구
        is_alert_required (Boolean): 이수한 요건 갯수가 미달이거나 경계 시 화면에 경고 알림 노출 여부
        logic_operator (String): 타 조건 그룹들과 AND 할지 OR 통과 처리할 지 결정
        
        department (relationship): 위 요건을 주관하는 학과 정보 객체 (N:1)
        requirement_courses (relationship): 이 조건 그룹에 대상이 되는/포함되는 과목들 목록 (1:N)
    """
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
    """
    요건정의 그룹(DepartmentEntryRequirement) 내부에서 실제 인정/대상으로 편입되는 'N개의 과목'과 1:N 매핑 처리하는 연결 모델입니다.

    Attributes:
        id (Integer): 매핑 식별 ID 번호 (PK)
        requirement_id (Integer): 모체가 되는 진입 요건 룰/그룹의 ID 번호 (FK, CASCADE 삭제)
        course_code (String): 통과/이수 대상으로 삼는 개별 대상 과목의 학수번호 (FK)
        
        requirement (relationship): 부모 진입 요건 그룹 (N:1)
        course (relationship): 매핑되는 실제 대상 수업/과목 엔티티 (N:1)
    """
    __tablename__ = "requirement_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("department_entry_requirements.id", ondelete="CASCADE"), nullable=False)
    course_code = Column(String(20), ForeignKey("courses.course_code"), nullable=False)
    
    requirement = relationship("DepartmentEntryRequirement", back_populates="requirement_courses")
    course = relationship("Course")


class StudentRequirementStatus(Base):
    """
    AI 엔진이나 연산 모듈이 개별 학생의 특정 전공 맞춤형 만족률/충족도를 가심사평가해 캐싱하고 기록하는 결과 모델입니다.

    Attributes:
        id (Integer): 가심사 평가 캐시 데이터의 인덱스 식별 ID (PK)
        student_id (Integer): 진단의 주체 학생 학번 (FK)
        department_id (Integer): 평가 목표/기준점 학과 식별자 (FK)
        is_satisfied (Boolean): 요건 최종 통과 만족(가능) 여부 표시
        analysis_json (JSON): 과목별 이수 현황 등, 엔진이 상세 산출한 근거 데이터
        curriculum_completion_score (Numeric): 커리큘럼 기준/점수 퍼센티지 수치 (기존 레거시)
        related_courses_score (Numeric): 직/간접 연계 과목 부가점수 (기존 레거시)
        overall_score (Numeric): 합산 종합 점수 / 등급 판정을 위한 수(기존 레거시)
        ai_summary (Text): AI LLM API 등을 통해 도출된 맞춤 평단 코멘트 및 권장사항 텍스트
        calculated_at (DateTime): 해당 평가가 제일 최근 진행 및 저장된 시점
        
        student (relationship): 산출 기록의 타겟 학생 정보 (N:1)
        department (relationship): 산출 기록의 타겟 전공 정보 (N:1)
    """
    __tablename__ = "student_requirement_status"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
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
    """
    학과별로 각 수강학년 등에 맞추어 구성된 권장 표준 교육과정(트랙/커리큘럼)을 구성하는 모델입니다.

    Attributes:
        id (Integer): 교육과정 항목 마스터 식별자 (PK)
        department_id (Integer): 커리큘럼에 소속된 주관 학과 인덱스 (FK)
        course_year (Integer): 몇 학년 때 이수해야 하는지 지정 (예: 1, 2)
        course_code (String): 실제 권장 수업되는 과목 코드 명
        course_name (String): 권장 과목명칭
        credits (Integer): 과목 인정 학점 
        course_type (String): 커리큘럼 내부 이수 분류 속성
        semester (Integer): 개설 진행 추천 학기
        
        department (relationship): 해당 커리큘럼의 주인 학과 정보 (N:1)
    """
    __tablename__ = "curriculums"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    course_year = Column(Integer, nullable=False)  # 1, 2, 3, 4학년
    course_code = Column(String(20), nullable=False)
    course_name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False, default=3)
    course_type = Column(String(30), nullable=True)
    semester = Column(Integer, nullable=False, default=1)
    
    department = relationship("Department")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'course_code', name='uq_curriculum_dept_course'),
    )


class CourseRecommendation(Base):
    """
    학과별로 전공 진입 혹은 적응을 위해 별개로 권하는 부가적 추천 과목 모음을 정의하는 모델입니다.

    Attributes:
        id (Integer): 권장 데이터의 1차 키 설정값 (PK)
        department_id (Integer): 추천을 진행하는 대상 학과의 인덱스 (FK)
        course_name (String): 추천되거나 도움된다고 안내되는 과목 명칭
        
        department (relationship): 이 객체와 연결된 학과 모델 참조 (N:1)
    """
    __tablename__ = "course_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    course_name = Column(String(100), nullable=False)
    
    department = relationship("Department")
    
    __table_args__ = (
        UniqueConstraint('department_id', 'course_name', name='uq_recommendation_dept_course'),
    )
