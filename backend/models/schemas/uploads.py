"""
대량 업로드/동기화 입력 DTO. (models/schemas 에서 분리)
"""

from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# Base Response Models

class MajorSurveyDataUpload(BaseModel):
    """
    엑셀/CSV를 통해 학생의 희망 전공 지망 이력을 업로드할 때 사용되는 스키마입니다.

    Attributes:
        id (Optional[int]): DB에 이미 있을 경우 갱신용 ID
        student_id (int): 학생 학번 (허용 열: "student_id", "학번")
        survey_round_id (int): 설문 회차 식별자 (허용 열: "survey_round_id", "회차" 등)
        first_choice_id (int): 1지망 학과 식별자 ID
        second_choice_id (int): 2지망 학과 식별자 ID
        decision_status_id (Optional[int]): 결정 상태 코드 식별자 
        decision_scale (Optional[int]): 전공결정 척도(리커트 척도)
    """
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID"))
    student_id: int = Field(..., validation_alias=AliasChoices("student_id", "학번"))
    survey_round_id: int = Field(..., validation_alias=AliasChoices("survey_round_id", "survey_round", "회차", "회차ID"))
    first_choice_id: int = Field(..., validation_alias=AliasChoices("first_choice_id", "1지망", "1지망학과", "1지망학과ID", "1지망 학과 ID"))
    second_choice_id: int = Field(..., validation_alias=AliasChoices("second_choice_id", "2지망", "2지망학과", "2지망학과ID", "2지망 학과 ID"))
    decision_status_id: Optional[int] = Field(None, validation_alias=AliasChoices("decision_status_id", "결정상태", "결정상태ID"))
    decision_scale: Optional[int] = Field(None, validation_alias=AliasChoices("decision_scale", "결정척도", "리커트 척도"))

    model_config = {"populate_by_name": True}


class StudentDataUpload(BaseModel):
    """
    엑셀/CSV 등으로 여러 학생의 기본 정보를 대량 업로드할 때 사용하는 스키마입니다.

    Attributes:
        student_id (int): 학생의 고유 학번 (지원 열: "student_id", "학번")
        name (str): 학생의 실명 (지원 열: "name", "이름", "성명")
        email (EmailStr): 학교 혹은 개인 이메일 주소 (지원 열: "email", "이메일")
        phone (Optional[str]): 학생의 연락처 (지원 열: "phone", "연락처", "전화번호")
        department_id (int): 소속 학과의 고유 식별자 (지원 열: "department_id", "소속학과" 등)
        advisor_id (Optional[int]): 지도 교수의 고유 ID 
        pride (Optional[str]): 학생의 PRIDE/LIONSE 등급 속성
        class_number (Optional[int]): 수강하는 핵심 분반 정보 
        track (Optional[str]): 입학 시 등록된 트랙(예: 자유전공 등)
    """
    student_id: int = Field(..., validation_alias=AliasChoices("student_id", "학번"))
    name: str = Field(..., validation_alias=AliasChoices("name", "이름", "성명"))
    email: EmailStr = Field(..., validation_alias=AliasChoices("email", "이메일"))
    phone: Optional[str] = Field(None, validation_alias=AliasChoices("phone", "연락처", "전화번호"))
    department_id: int = Field(..., validation_alias=AliasChoices("department_id", "소속학과", "학과ID", "소속 학과 ID"))
    advisor_id: Optional[int] = Field(None, validation_alias=AliasChoices("advisor_id", "지도교수ID", "지도교수 ID"))
    pride: Optional[str] = Field(None, validation_alias=AliasChoices("pride", "PRIDE", "LIONSE", "LIONSE 등급"))
    class_number: Optional[int] = Field(None, validation_alias=AliasChoices("class", "class_number", "분반"))
    track: Optional[str] = Field(None, validation_alias=AliasChoices("track", "계열", "전공트랙"))

    model_config = {"populate_by_name": True}


class EnrollmentDataUpload(BaseModel):
    """
    엑셀/CSV 등을 통한 학생의 학기별/과목별 수강 내역을 업로드할 때 사용되는 스키마입니다.

    Attributes:
        id (Optional[int]): DB에 존재 시 덮어쓰기 위해 제공되는 PK
        student_id (int): 학생 식별 번호
        course_code (str): 수강 당시의 과목 학수번호
        course_name (str): 수강 당시의 과목명
        credits (int): 취득/수강 신청한 학점 수
        year (int): 수강한 학사 연도
        semester (int): 학기 수
        completion_type (str): 이수 구분 (예: 교필, 교선)
        is_retake (bool): 재수강 여부
        grade (Optional[str]): 성적 등급 기호(A+, C+ 등)
        numeric_grade (Optional[float]): 평점 점수 정보(4.5 등)
    """
    id: Optional[int] = None
    student_id: int = Field(..., validation_alias=AliasChoices("student_id", "학번"))
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드", "과목번호", "교과목번호"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목명", "교과목 이름"))
    credits: int = Field(3, validation_alias=AliasChoices("credits", "학점", "신청학점"))
    year: int = Field(..., validation_alias=AliasChoices("year", "년도", "수강년도", "학년도", "연도", "수강학기기준연도"))
    semester: int = Field(..., validation_alias=AliasChoices("semester", "학기", "수강학기"))
    completion_type: str = Field(..., validation_alias=AliasChoices("completion_type", "이수구분", "수강구분", "이수"))
    is_retake: bool = Field(False, validation_alias=AliasChoices("is_retake", "재수강여부", "재수강", "재수강구분"))
    grade: Optional[str] = Field(None, validation_alias=AliasChoices("grade", "성적", "등급", "성적등급"))
    numeric_grade: Optional[float] = Field(None, validation_alias=AliasChoices("numeric_grade", "평점", "성적평점", "점수"))

    model_config = {"populate_by_name": True}


class CurriculumDataUpload(BaseModel):
    """
    엑셀/CSV를 통해 전공별/학년별 권장 교육과정 정보(커리큘럼)를 업로드하기 위한 스키마입니다.

    Attributes:
        department_code (Optional[str]): 개설/주관 학과의 코드
        department_id (Optional[int]): 주관 학과의 ID
        course_year (int): 언제 수강하는 것을 권장하는지 나타내는 권장 학년
        course_code (str): 과목의 고유 학수번호
        course_name (str): 과목의 이름
        credits (int): 과목 학점
        course_type (Optional[str]): 해당 학과 내에서의 이수 구분(전필, 전선 등)
        semester (int): 언제 수강하는 것을 권장하는지 나타내는 권장 학기
    """
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code", "학과코드", "소속학과", "학과", "설강학과"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID", "교육과정학과코드"))
    course_year: int = Field(..., validation_alias=AliasChoices("course_year", "권장학년", "학년", "수강학년"))
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드", "교과목번호"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목명"))
    credits: int = Field(3, validation_alias=AliasChoices("credits", "학점"))
    course_type: Optional[str] = Field(None, validation_alias=AliasChoices("course_type", "이수구분", "구분", "과목구분", "과목유형"))
    semester: int = Field(1, validation_alias=AliasChoices("semester", "권장학기", "학기", "수강학기"))

    model_config = {"populate_by_name": True}


class RecommendationDataUpload(BaseModel):
    """
    엑셀/CSV를 통하여 특정 학과의 전공 진입을 위한 전체 권장 과목 목록을 손쉽게 올리기 위한 스키마입니다.

    Attributes:
        id (Optional[int]): 갱신 시 주어지는 레코드 PK
        department_code (Optional[str]): 전공 진입 대상 선호 학과 코드
        department_id (Optional[int]): 전공 진입 대상 학과 식별자
        course_name (str): 권장하여 듣게끔 유도되는 과목 명칭
    """
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID", "권장과목ID"))
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code", "학과코드", "소속학과", "학과"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목 이름", "교과목명"))

    model_config = {"populate_by_name": True}


class RequirementDataUpload(BaseModel):
    """
    전공 진입 심사를 위해, 입학년도별 학과의 수강 요건 그룹 정보를 대량으로 업로드하는 스키마입니다.

    Attributes:
        id (Optional[int]): 레코드 고유 ID
        department_code (Optional[str]): 대상 학과 구별 코드
        department_id (Optional[int]): 대상 학과 식별자 고유 번호
        admission_year (int): 어느 입학년도의 학생부터 적용되는 규칙인지를 나타냄
        requirement_group (int): 1차, 2세부 요건 등을 구별하는 논리적 묶음 단위
        target_grade_level (str): 평점이 특정 수준을 넘겨야 하는 경우 기재
        required_count (int): 이 요건 그룹 내에서 반드시 수강해야 하는 최소 과목의 수
        requirement_text (str): 텍스트 요건 설명
        is_alert_required (bool): 관리자/학생이 확인할 시 놓쳤을 때 안내를 내릴 지 여부
        logic_operator (str): 다수 요건 그룹 간 AND/OR 병합 처리를 위한 연산자
    """
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID", "요건ID"))
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code", "dept_code", "학과코드", "소속학과", "학과"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID"))
    admission_year: int = Field(..., validation_alias=AliasChoices("admission_year", "적용학번", "적용 학번"))
    requirement_group: int = Field(..., validation_alias=AliasChoices("requirement_group", "요건그룹", "요건 그룹", "그룹"))
    target_grade_level: str = Field(..., validation_alias=AliasChoices("target_grade_level", "기준성적", "기준 성적"))
    required_count: int = Field(..., validation_alias=AliasChoices("required_count", "충족과목수", "요구과목수", "필수 과목 수"))
    requirement_text: str = Field(..., validation_alias=AliasChoices("requirement_text", "요건설명", "설명"))
    is_alert_required: bool = Field(False, validation_alias=AliasChoices("is_alert_required", "알림여부", "알림창 여부"))
    logic_operator: str = Field("AND", validation_alias=AliasChoices("logic_operator", "논리연산자", "조건"))

    model_config = {"populate_by_name": True}

class RequirementCourseDataUpload(BaseModel):
    """
    생성된 학과별 요건 그룹(RequirementDataUpload)에 개별 과목을 맵핑하여 올릴 때 쓰는 스키마입니다.

    Attributes:
        id (Optional[int]): 맵핑 테이블 고유 식별자
        requirement_id (int): 전제조건이 되는 요건 그룹 정보 ID
        course_code (str): 요건 적용 대상으로 포함될 과목의 고유 학수번호
    """
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID", "매핑ID"))
    requirement_id: int = Field(..., validation_alias=AliasChoices("requirement_id", "요건 ID", "요건ID"))
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드", "과목번호"))

    model_config = {"populate_by_name": True}


class CollegeDataUpload(BaseModel):
    """
    단과대학 기본 정보를 대량으로 업로드/동기화할 때 사용하는 스키마입니다.

    Attributes:
        id (Optional[int]): 데이터베이스에서의 고유값
        name (str): 새로 등록/수정될 단과대학 이름
    """
    id: Optional[int] = None
    name: str


class AdvisorDataUpload(BaseModel):
    """
    지도교수 상세 데이터를 대용량 엑셀/CSV로 업로드할 때 매핑되는 스키마입니다.

    Attributes:
        id (Optional[int]): 지도 교수의 고유 번호
        name (str): 실명
        email (Optional[str]): 소속 이메일 등
        department_id (Optional[int]): 속한 학과의 ID
    """
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "교수ID", "ID"))
    name: str = Field(..., validation_alias=AliasChoices("name", "이름", "교수명", "성명"))
    email: Optional[str] = Field(None, validation_alias=AliasChoices("email", "이메일"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID"))

    model_config = {"populate_by_name": True}


class DepartmentDataUpload(BaseModel):
    """
    새로운 학과 데이터들이나 학과별 기초 정보(졸업학점 등)를 엑셀 업로드할 때의 스키마입니다.

    Attributes:
        id (Optional[int]): 학과 ID
        code (str): 학과 코드(CS, AI 등)
        name (str): 학과 이름
        college_name (Optional[str]): 참조가 될 단과대명 (문자열)
        college_id (Optional[int]): 참조가 되는 단과대 ID
        min_credits (int): 최소 이수 총 요구 학점 (기본값: 130)
    """
    id: Optional[int] = None
    code: str
    name: str
    college_name: Optional[str] = None  # college name으로 매칭
    college_id: Optional[int] = None  # 또는 college_id 직접 지정
    min_credits: int = 130


class CourseDataUpload(BaseModel):
    """
    전체 교과목 모음전 단위 업로드/포팅을 위해 모든 과목 정보를 맵핑하는 엑셀용 스키마입니다.

    Attributes:
        course_code (str): 학수번호
        course_name (str): 신설되거나 갱신될 과목의 이름
        course_type (Optional[str]): 이수 구분 유형 기호(전선, 일선 등)
        course_year (Optional[int]): 권장 학년
        department_name (Optional[str]): 운영 주관 학과 명
        department_code (Optional[str]): 주관 학과 코드
        credits (Optional[int]): 이수 시 부여되는 학점
        description (Optional[str]): 과목 설명(교과 개요)
        prerequisite (Optional[str]): 선수 요구 조건이 있을 경우 그 텍스트나 과목명
    """
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목 이름", "교과목명"))
    course_type: Optional[str] = Field(None, validation_alias=AliasChoices("course_type", "이수구분"))
    course_year: Optional[int] = Field(None, validation_alias=AliasChoices("course_year", "학년", "권장학년", "권장 학년"))
    department_name: Optional[str] = Field(None, validation_alias=AliasChoices("department_name", "설강학과", "관장학과"))
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code"))
    credits: Optional[int] = Field(None, validation_alias=AliasChoices("credits", "학점"))
    description: Optional[str] = Field(None, validation_alias=AliasChoices("description", "교과목개요", "개요"))
    prerequisite: Optional[str] = Field(None, validation_alias=AliasChoices("prerequisite", "선수강 과목", "선수과목"))

    model_config = {"populate_by_name": True}
