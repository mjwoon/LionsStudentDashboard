from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# Base Response Models
class CollegeBase(BaseModel):
    """
    단과대학 기본 정보를 담는 스키마입니다.

    Attributes:
        id (int): 단과대학의 고유 식별자 (PK)
        name (str): 단과대학의 이름
    """
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class DepartmentBase(BaseModel):
    """
    학과 기본 정보를 담는 스키마입니다.

    Attributes:
        id (int): 학과의 고유 식별자 (PK)
        name (str): 학과 이름
    """
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class DepartmentDetail(BaseModel):
    """
    학과의 상세 정보를 담는 스키마입니다.

    Attributes:
        id (int): 학과의 고유 식별자 (PK)
        code (str): 학과 코드
        name (str): 학과 이름
        college_name (str): 소속 단과대학의 이름
        min_credits (int): 졸업을 위한 최소 이수 학점
        is_evaluation_available (bool): AI 전공진입 적합도 평가가 가능한 학과인지 여부
    """
    id: int
    code: str
    name: str
    college_name: str
    min_credits: int
    is_evaluation_available: bool = False

    model_config = ConfigDict(from_attributes=True)


class AcademicInfo(BaseModel):
    """
    학생의 학사 관련 상세 정보를 담는 스키마입니다.

    Attributes:
        pride (str): 학생의 PRIDE(LIONSE 등급) 정보
        class_number (int): 분반 정보
        track (Optional[str]): 전공 트랙 (예: 전계열, 자연계열, 인문사회계열 등)
        advisor_id (Optional[int]): 지도교수 ID
        advisor_name (Optional[str]): 지도교수 이름
        status (str): 학적 상태 (기본값: "재학")
        updated_at (Optional[datetime]): 마지막 학사 정보 업데이트 일시
    """
    pride: str
    class_number: int
    track: Optional[str] = None  # 전계열, 자연계열, 인문사회계열
    advisor_id: Optional[int] = None
    advisor_name: Optional[str] = None
    status: str = "재학"
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Student Models
class StudentBase(BaseModel):
    """
    학생 기본 정보를 담는 스키마입니다.

    Attributes:
        student_id (int): 학생의 고유 학번 (PK)
        name (str): 학생의 이름
        email (EmailStr): 이메일 주소
        phone (Optional[str]): 연락처
    """
    student_id: int  # Integer PK
    name: str
    email: EmailStr
    phone: Optional[str] = None


class StudentCreate(StudentBase):
    """
    새로운 학생을 생성할 때 사용하는 스키마입니다.

    Attributes:
        department_id (int): 소속 학과 ID
        advisor_id (Optional[int]): 지도교수 ID
        pride (str): 학생의 PRIDE(LIONSE 등급) 정보
        class_number (int): 분반
    """
    department_id: int
    advisor_id: Optional[int] = None
    pride: str
    class_number: int


class StudentInList(StudentBase):
    """
    학생 목록 조회 시 반환되는 학생 정보를 담는 스키마입니다.

    Attributes:
        department (DepartmentBase): 소속 학과 정보
        academic_info (AcademicInfo): 세부 학사 정보
        latest_major_choice (Optional[str]): 최신 희망 학과
        decision_certainty (Optional[int]): 전공결정도 (1-5 척도)
        completion_status (Optional[str]): 이수현황 (예: "15/20")
        course_suitability (Optional[str]): 수강과목 적합성 (예: "양호")
    """
    department: DepartmentBase
    academic_info: AcademicInfo
    latest_major_choice: Optional[str] = None  # 최신 희망 학과
    decision_certainty: Optional[int] = None  # 전공결정도 (1-5)
    completion_status: Optional[str] = None  # 이수현황 (예: "15/20")
    course_suitability: Optional[str] = None  # 수강과목 적합성 (예: "양호")

    model_config = ConfigDict(from_attributes=True)


class StudentDetail(StudentBase):
    """
    학생의 상세 조회 시 반환되는 정보를 담는 스키마입니다.

    Attributes:
        department (DepartmentBase): 소속 학과 상세 정보
        academic_info (AcademicInfo): 세부 학사 정보
    """
    department: DepartmentBase
    academic_info: AcademicInfo

    model_config = ConfigDict(from_attributes=True)


class StudentListResponse(BaseModel):
    """
    학생 목록 조회에 대한 페이지네이션 응답 스키마입니다.

    Attributes:
        count (int): 전체 학생 수
        page (int): 현재 페이지 번호
        per_page (int): 페이지당 항목 수
        students (List[StudentInList]): 학생 목록
    """
    count: int
    page: int
    per_page: int
    students: List[StudentInList]


class StudentCreateResponse(BaseModel):
    """
    학생 생성 처리 결과에 대한 응답 스키마입니다.

    Attributes:
        message (str): 처리 결과 메시지
        student_id (int): 생성된 학생의 학번
    """
    message: str
    student_id: int


# Course Models
class CourseFlags(BaseModel):
    """
    과목과 관련된 부가 속성(플래그)을 담는 스키마입니다.

    Attributes:
        is_retake_only (bool): 해당 과목이 재수강 전용인지 여부
    """
    is_retake_only: bool


class CourseBase(BaseModel):
    """
    과목 기본 정보를 담는 스키마입니다.

    Attributes:
        course_id (int): 과목의 고유 식별자 (PK)
        course_code (str): 학수번호 (과목코드)
        course_name (str): 과목 이름
        credits (int): 학점
        course_type (str): 이수구분 (예: 전공필수, 교양선택 등)
    """
    course_id: int
    course_code: str
    course_name: str
    credits: int
    course_type: str


class CourseInList(CourseBase):
    """
    과목 목록 조회 시 반환되는 과목 정보를 담는 스키마입니다.

    Attributes:
        department (DepartmentBase): 과목을 개설한 관장학과 정보
        flags (CourseFlags): 과목의 기타 속성 플래그
        description (Optional[str]): 과목 내용 개요
    """
    department: DepartmentBase
    flags: CourseFlags
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseListResponse(BaseModel):
    """
    과목 목록 조회에 대한 페이지네이션 응답 스키마입니다.

    Attributes:
        count (int): 전체 과목 수
        page (int): 현재 페이지 번호
        per_page (int): 페이지당 학목 수
        courses (List[CourseInList]): 과목 목록
    """
    count: int
    page: int
    per_page: int
    courses: List[CourseInList]


class CourseEnrollmentDetail(BaseModel):
    """
    학생의 특정 과목 수강 내역에 대한 상세 정보를 담는 스키마입니다.

    Attributes:
        course_id (int): 과목 식별자
        course_code (str): 학수번호
        course_name (str): 과목 이름
        credits (int): 취득 학점 수
        year (int): 수강 연도
        semester (int): 수강 학기
        completion_type (str): 이수구분 (예: 전필, 전선 등)
        is_retake (bool): 재수강 여부
        grade (Optional[str]): 취득 등급 (예: A+, B0)
        numeric_grade (Optional[float]): 취득 평점 (예: 4.5, 3.0)
    """
    course_id: int
    course_code: str
    course_name: str
    credits: int
    year: int
    semester: int
    completion_type: str
    is_retake: bool
    grade: Optional[str] = None
    numeric_grade: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class StudentCoursesResponse(BaseModel):
    """
    특정 학생의 전체 수강 내역을 조회할 때 반환되는 스키마입니다.

    Attributes:
        student_id (int): 조회 학생의 고유 학번
        total_credits (int): 누적 총 이수 학점
        course_history (List[CourseEnrollmentDetail]): 수강 이력 상세
    """
    student_id: int
    total_credits: int
    course_history: List[CourseEnrollmentDetail]


class EntryRequirementCourse(BaseModel):
    """
    전공 진입을 위해 필수로 또는 권장하여 이수해야 하는 과목들의 정보를 담는 스키마입니다.

    Attributes:
        course_id (int): 과목 식별자
        course_code (str): 학수번호
        course_name (str): 과목명
        credits (int): 학점
        course_type (str): 과목의 이수구분
        department_id (int): (요구하는) 학과의 식별자
        department_name (str): 학과명
        is_recommended (bool): 필수 요건인지(False) 단순히 권장인지(True)의 여부
    """
    course_id: int
    course_code: str
    course_name: str
    credits: int
    course_type: str
    department_id: int
    department_name: str
    is_recommended: bool

    model_config = ConfigDict(from_attributes=True)


class EntryRequirementsResponse(BaseModel):
    """
    전공 진입 요건(필수/권장 과목) 목록 응답을 위한 스키마입니다.

    Attributes:
        count (int): 전체 과목 수
        courses (List[EntryRequirementCourse]): 진입 요건 과목 목록
    """
    count: int
    courses: List[EntryRequirementCourse]


# Department Models
class DepartmentListResponse(BaseModel):
    """
    전체 학과 목록 조회 시 반환되는 래퍼 스키마입니다.

    Attributes:
        count (int): 전체 학과 수
        departments (List[DepartmentDetail]): 학과 상세 목록 
    """
    count: int
    departments: List[DepartmentDetail]


class DepartmentCurriculum(BaseModel):
    """
    학과의 교육과정 및 전공 진입 관련 기본 정보를 담는 스키마입니다.

    Attributes:
        department_name (str): 학과 이름
        graduation_min_credits (int): 최소 졸업 학점
        tracks (List[str]): 학과 내 전공 트랙 목록
        entry_requirements_description (str): 전공 진입 요건에 대한 설명 텍스트
    """
    department_name: str
    graduation_min_credits: int
    tracks: List[str]
    entry_requirements_description: str


# Survey Models
class SurveyChoiceBase(BaseModel):
    """
    설문조사의 선택지(학과) 기본 정보를 담는 스키마입니다.

    Attributes:
        id (int): 선택지(학과)의 식별자
        name (str): 선택지(학과)의 이름
    """
    id: int
    name: str


class SurveyHistoryItem(BaseModel):
    """
    학생의 과거 설문 참여 응답 내역의 단건 정보를 담는 스키마입니다.

    Attributes:
        survey_id (int): 설문 응답의 고유 식별자
        round (int): 설문 회차
        submitted_at (str): 제출 일시
        first_choice (SurveyChoiceBase): 1지망 학과 정보
        second_choice (Optional[SurveyChoiceBase]): 2지망 학과 정보 (선택)
        decision_scale (int): 전공 결정에 대한 확신도(리커트 척도)
    """
    survey_id: int
    round: int
    submitted_at: str
    first_choice: SurveyChoiceBase
    second_choice: Optional[SurveyChoiceBase] = None
    decision_scale: int

    model_config = ConfigDict(from_attributes=True)


class StudentSurveysResponse(BaseModel):
    """
    특정 학생의 설문 조사 전체 참여 내역을 담는 응답 스키마입니다.

    Attributes:
        history (List[SurveyHistoryItem]): 전체 설문 응답 내역
    """
    history: List[SurveyHistoryItem]


class SurveyCreate(BaseModel):
    """
    새로운 설문 응답을 생성(제출)할 때 사용하는 스키마입니다.

    Attributes:
        student_id (int): 설문에 참여하는 학생의 학번
        first_choice_dept_id (str): 1지망 학과 ID (문자열 형식)
        second_choice_dept_id (Optional[str]): 2지망 학과 ID (문자열 형식, 선택)
        survey_round (int): 응답하는 설문의 회차
        decision_scale (int): 전공 결정도 (척도)
    """
    student_id: int
    first_choice_dept_id: str
    second_choice_dept_id: Optional[str] = None
    survey_round: int
    decision_scale: int


class SurveySubmitData(BaseModel):
    """
    설문 제출 후 반환되는 요약 정보 스키마입니다.

    Attributes:
        survey_id (int): 생성된 설문 데이터의 식별자
        submitted_at (str): 제출 완료 시각
    """
    survey_id: int
    submitted_at: str


class SurveyCreateResponse(BaseModel):
    """
    설문 제출 처리 결과의 응답 스키마입니다.

    Attributes:
        success (bool): 성공 여부
        message (str): 처리 결과 메시지
        data (SurveySubmitData): 생성된 설문 정보
    """
    success: bool
    message: str
    data: SurveySubmitData


class MajorPreference(BaseModel):
    """
    학과별 선호도 요약 정보를 담는 스키마입니다. (통계용)

    Attributes:
        dept_name (str): 학과 명
        count (int): 해당 학과 지망 학생 수
        avg_decision_scale (float): 해당 학과 지망생들의 전공결정도 평균
    """
    dept_name: str
    count: int
    avg_decision_scale: float


class SurveyStatus(BaseModel):
    """
    현재 진행 중인 설문 조사 현황/상태 정보를 나타내는 스키마입니다.

    Attributes:
        current_round (int): 현재 진행 중인/최신 설문 회차
        participation_rate (float): 전체 학생 대비 제출 비율 (참여율 등)
    """
    current_round: int
    participation_rate: float


class SurveyOverview(BaseModel):
    """
    전체 설문 조사 및 진입요건 대상 정보에 대한 개괄적 통계 스키마입니다.

    Attributes:
        total_students (int): 설문 대상 혹은 전체 학생 수
        total_departments (int): 전체 학과 수
        entry_requirement_completion_rate (float): 전공 진입 요건 만족률
    """
    total_students: int
    total_departments: int
    entry_requirement_completion_rate: float


class SurveySummaryResponse(BaseModel):
    """
    설문조사에 대한 종합 통계 응답 스키마입니다.

    Attributes:
        overview (SurveyOverview): 기본 통계 개괄 정보
        major_preferences (List[MajorPreference]): 각 학과별 지망도/결정척도
        survey_status (SurveyStatus): 설문 회차 및 현황
    """
    overview: SurveyOverview
    major_preferences: List[MajorPreference]
    survey_status: SurveyStatus


class SurveySubmissionItem(BaseModel):
    """
    전체 설문내역 조회 화면 등에서 보여주기 위한 단일 응답 항목 스키마입니다.

    Attributes:
        survey_id (int): 설문 응답 식별자
        student_id (int): 학생 학번
        name (str): 학생 이름
        department_name (str): 학생의 현재 소속
        first_choice (SurveyChoiceBase): 1지망 선택지
        second_choice (Optional[SurveyChoiceBase]): 2지망 선택지
        decision_scale (int): 전공 선택 확신 척도
        submitted_at (str): 제출 일시
    """
    survey_id: int
    student_id: int
    name: str
    department_name: str
    first_choice: SurveyChoiceBase
    second_choice: Optional[SurveyChoiceBase] = None
    decision_scale: int
    submitted_at: str

    model_config = ConfigDict(from_attributes=True)


class RoundInfo(BaseModel):
    """
    설문 회차 정보를 제공하는 스키마입니다.

    Attributes:
        round_id (int): 설문 회차 ID
        title (str): 설문 회차의 제목/명칭
        status (str): 진행 상태
    """
    round_id: int
    title: str
    status: str


class SurveyRoundMeta(BaseModel):
    """
    특정 설문 회차 조회에 대한 페이지네이션 및 메타데이터 스키마입니다.

    Attributes:
        total_count (int): 전체 제출 수
        current_page (int): 현재 페이지 수
        total_pages (int): 총 페이지 수
        per_page (int): 페이지당 항목 수
    """
    total_count: int
    current_page: int
    total_pages: int
    per_page: int = 20


# Dashboard Statistics Models
class DepartmentWithStats(BaseModel):
    """
    대시보드에서 학과별 인원 통계 지표를 나타내는 스키마입니다.

    Attributes:
        id (str): 학과 식별자
        name (str): 학과 이름
        college (str): 소속 단과대학
        color (str): 대시보드 그래프 표시용 색상 코드
        students (int): 해당 학과 지망 혹은 소속 학생 수
        percent (float): 전체 대비 해당 학과 비중
    """
    id: str
    name: str
    college: str
    color: str
    students: int
    percent: float

    model_config = ConfigDict(from_attributes=True)


class TrendDataPoint(BaseModel):
    """
    기간별/회차별 지망 학과 추이 데이터를 나타내는 스키마입니다.

    Attributes:
        period (str): 기준 기간 명칭 (예: "1차", "2차" 등)
        data (dict): key=학과ID, value=해당 시기의 지망 학생 수 맵핑
    """
    period: str
    data: dict  # department_id: count

    model_config = ConfigDict(from_attributes=True)


class SurveyRoundInfo(BaseModel):
    """
    대시보드 등에서 사용하는 설문 회차에 대한 상세 설정 및 상태 스키마입니다.

    Attributes:
        round_number (int): 회차 번호
        title (str): 회차 제목
        status (str): 현재 상태
        end_date (Optional[str]): 설문 종료일
    """
    round_number: int
    title: str
    status: str
    end_date: Optional[str] = None


class SurveyRoundSummary(BaseModel):
    """
    설문 회차의 간략한 요약 데이터를 제공하는 스키마입니다.

    Attributes:
        round_number (int): 회차 번호
        title (str): 회차 제목
    """
    round_number: int
    title: str


class DashboardStatsResponse(BaseModel):
    """
    관리자 대시보드 화면에 필요한 종합적인 통계 수치를 묶어서 반환하는 응답 스키마입니다.

    Attributes:
        colleges (List[CollegeBase]): 단과대학 목록정보
        departments (List[DepartmentWithStats]): 전체 학과 및 통계 비교 목록
        current_data (List[DepartmentWithStats]): 현재 최신 회차의 지망 학과 통계
        trend_data (List[TrendDataPoint]): 누적/시기별 트렌드 추이
        survey_info (Optional[SurveyRoundInfo]): 현재 진행중인 주요 설문 상태 (선택)
        survey_rounds (Optional[List[SurveyRoundSummary]]): 과거 설문 회차 리스트 (선택)
        current_data_by_round (Optional[Dict[int, List[DepartmentWithStats]]]): 회차 번호별 집계 내역 (선택)
    """
    colleges: List[CollegeBase]
    departments: List[DepartmentWithStats]
    current_data: List[DepartmentWithStats]
    trend_data: List[TrendDataPoint]
    survey_info: Optional[SurveyRoundInfo] = None
    survey_rounds: Optional[List[SurveyRoundSummary]] = None
    current_data_by_round: Optional[Dict[int, List[DepartmentWithStats]]] = None

    model_config = ConfigDict(from_attributes=True)


class SurveyRoundResponse(BaseModel):
    """
    특정 회차 설문 내역 목록을 조회할 때 사용하는 응답 스키마입니다.

    Attributes:
        meta (SurveyRoundMeta): 목록 페이지네이션 정보
        round_info (RoundInfo): 해당 회차의 기본 정보
        submissions (List[SurveySubmissionItem]): 개별 설문 응답 건 목록
    """
    meta: SurveyRoundMeta
    round_info: RoundInfo
    submissions: List[SurveySubmissionItem]


# Department Entry Requirements Models
class RequirementCourseDetail(BaseModel):
    """
    특정 요건과 연결된 권장/필수 과목 상세 정보를 담는 스키마입니다.

    Attributes:
        course_code (str): 학수번호
        course_name (str): 과목 이름
        credits (int): 해당 과목의 학점
    """
    course_code: str
    course_name: str
    credits: int

    model_config = ConfigDict(from_attributes=True)


class DepartmentEntryRequirementDetail(BaseModel):
    """
    학과의 전공 진입 요건 그룹 구성과 상세 정보를 담는 스키마입니다.

    Attributes:
        id (int): 요건 식별자 (PK)
        department_id (int): 학과 식별자
        department_name (str): 학과 명칭
        admission_year (int): 해당 요건이 기준선으로 적용되는 입학년도
        requirement_group (int): 요건이 속한 그룹의 번호
        target_grade_level (str): 기준 점수 (예컨대 "B0" 이상 등의 요구 조건)
        required_count (int): 해당 요건 그룹 중 필수 충족해야 하는 이수 과목 수
        requirement_text (str): 요건 설명 문구
        is_alert_required (bool): 사용자에게 경고(알림)를 통해 요건 누락을 알릴지 여부
        courses (List[RequirementCourseDetail]): 이 요건을 맞추기 위해 선택/이수할 수 있는 과목 목록
    """
    id: int
    department_id: int
    department_name: str
    admission_year: int
    requirement_group: int
    target_grade_level: str
    required_count: int
    requirement_text: str
    is_alert_required: bool
    courses: List[RequirementCourseDetail]

    model_config = ConfigDict(from_attributes=True)


# Student Requirement Status Models
class StudentRequirementStatusDetail(BaseModel):
    """
    특정 학생의 학과 진입 요건 충족 상태(가심사 결과 등)를 저장/반환하는 스키마입니다.

    Attributes:
        id (int): 상태 기록 이력 엔티티의 식별자
        student_id (int): 판별 대상 학생 학번
        department_id (int): 조준(가심사) 학과 ID
        department_name (str): 학과 이름
        is_satisfied (bool): 모든 요건을 만족하여 진입 가능한 상태인지 여부
        analysis_json (Optional[dict]): 평가 상세 결과/근거에 대한 구조화된 데이터(JSON 포맷 딕셔너리)
        ai_summary (Optional[str]): AI 평가 등에 의해 생성된 요약 코멘트
        calculated_at (datetime): 진단 연산이 수행된 일시
    """
    id: int
    student_id: int
    department_id: int
    department_name: str
    is_satisfied: bool
    analysis_json: Optional[dict] = None
    ai_summary: Optional[str] = None
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentRequirementStatusResponse(BaseModel):
    """
    한 학생의, (1지망 포함) 다수 학과에 대한 진단 이력/현황 묶음을 반환하는 응답 스키마입니다.

    Attributes:
        student_id (int): 대상 학생 고유 번호
        first_choice_dept_id (Optional[str]): 1지망 학과 ID 
        evaluations (List[StudentRequirementStatusDetail]): 여러 학과의 평가 이력 목록
    """
    student_id: int
    first_choice_dept_id: Optional[str] = None
    evaluations: List[StudentRequirementStatusDetail]


class MajorEvaluationSummary(BaseModel):
    """
    전공 진입 적합도 평가의 핵심 지표들을 요약하여 보여주는 스키마입니다.

    Attributes:
        required_courses_total (int): 들어야 할 총 필수과목 수
        required_courses_completed (int): 이수 완료한 필수과목 수
        required_courses_percentage (float): 필수과목 이수 진행률 수치
        missing_courses (List[dict]): 아직 듣지 않아 누락된 필수과목의 정보 목록
    """
    required_courses_total: int
    required_courses_completed: int
    required_courses_percentage: float
    missing_courses: List[dict]


class StudentMajorEvaluationResponse(BaseModel):
    """
    특정 학생의 한 학과에 대한 상세 전공진입 평가 결과를 반환하는 응답 스키마입니다.

    Attributes:
        student_id (int): 학생 식별자
        department_id (int): 평가 기준 소속 학과 식별자
        department_name (str): 학과 명칭
        evaluation (MajorEvaluationSummary): 필수과목 등의 평가 요약 정보
        entry_requirements (Optional[str]): 진입 요건 안내텍스트 
    """
    student_id: int
    department_id: int
    department_name: str
    evaluation: MajorEvaluationSummary
    entry_requirements: Optional[str] = None


# Evaluation Service Schemas
class RequiredCoursesResult(BaseModel):
    """
    필수 과목 기준에 대한 세부 평가 결과를 나타내는 스키마입니다.

    Attributes:
        score (float): 평가 점수 (필수 수강 부분의 산출 점수)
        total_requirements (int): 요구하는 총 요건 그룹/과목 수
        satisfied_requirements (int): 충족한 요건 수
        details (List[dict]): 요건별 만족 상세 내역
        pass_ (bool): 최종 합격 여부. JSON 직렬화 시 "pass" 키로 맵핑됨
        message (str): 결과 안내 문구
    """
    score: float
    total_requirements: int
    satisfied_requirements: int
    details: List[dict]
    pass_: bool = Field(default=None, alias='pass')
    message: str

    model_config = ConfigDict(populate_by_name=True)


class RecommendedCoursesResult(BaseModel):
    """
    권장 과목 기준에 대한 세부 평가 결과를 나타내는 스키마입니다.

    Attributes:
        score (float): 권장 과목에 대한 산출 평가 점수
        total_courses (int): 총 권장 과목 이수 요건
        completed_courses (int): 이수한 권장 과목 수
        total_credits (int): 권장 과목 총 학점
        completed_credits (int): 이수한 권장 학점 크기
        completion_rate (float): 달성률 %
        details (List[dict]): 상세 내역 정보
        message (str): 결과 안내 문구
    """
    score: float
    total_courses: int
    completed_courses: int
    total_credits: int
    completed_credits: int
    completion_rate: float
    details: List[dict]
    message: str


class RelatedCreditsResult(BaseModel):
    """
    그 외 관련 과목/전공 유사 학점 이수에 대한 평가 정보를 기록하는 스키마입니다.

    Attributes:
        score (float): 산출 점수
        total_available_credits (int): 최대 획득할 수 있는/전체 관련 학점량
        earned_credits (int): 실제로 학생이 얻은 학점
        message (str): 결과 안내 문구
        target_credits (Optional[float]): 목표로 삼는 기준 요구 이수 학점
    """
    score: float
    total_available_credits: int
    earned_credits: int
    message: str
    target_credits: Optional[float] = None


class EvaluationResultResponse(BaseModel):
    """
    AI 및 로직으로 산출된 최종 전공진입 적합도 진단 결과를 종합하여 담는 스키마입니다.

    Attributes:
        student_id (int): 학생 학번
        department_id (int): 맵핑되는 학과 ID
        department_name (str): 맵핑 학과 명
        admission_year (int): 대상이 되는 입학기준연도
        required_courses (dict): 필수 과목 상세 지표(RequiredCoursesResult 형태의 직렬화) 
        recommended_courses (dict): 권장 과목 상세 지표(RecommendedCoursesResult 형태의 직렬화)
        related_credits (dict): 기타 전공 및 관련학점 이수 내역 평가
        overall_score (float): 종합 백분위 점수 등 총점
        grade (str): 적합, 미흡 혹은 SABC 식의 평가 등급
        summary_message (str): 평가 핵심 요약 또는 평가자의 코멘트
        evaluated_at (datetime): 평가 수행 및 계산된 시각
    """
    student_id: int
    department_id: int
    department_name: str
    admission_year: int
    required_courses: dict
    recommended_courses: dict
    related_credits: dict
    overall_score: float
    grade: str
    summary_message: str
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchEvaluationRequest(BaseModel):
    """
    다수의 학생에 대해 비동기 배치로 진단을 수행하도록 요청하는 스키마입니다.

    Attributes:
        department_id (Optional[int]): 특정 과의 학생들만 제한할 시 사용. (None일 경우 전체 학생)
        admission_year (int): 진단 대상 입학 연도 기준 (기본값: 2025)
        limit_students (Optional[int]): 최대 진단 시도할 학생 수 제한 기능
    """
    department_id: Optional[int] = None
    admission_year: int = 2025
    limit_students: Optional[int] = None


class BatchEvaluationResponse(BaseModel):
    """
    배치 진단 수행 요청에 따른 피드백 스키마입니다.

    Attributes:
        department_id (int): 타겟 학과의 ID
        department_name (str): 타겟 학과 명칭
        total_students (int): 배치 처리가 진행된/예정인 학생 총 수
        saved_count (int): 데이터베이스에 진단이 새로 저장되거나 완료된 학생 수
        message (str): 처리 결과 메시지
    """
    department_id: int
    department_name: str
    total_students: int
    saved_count: int
    message: str


class StudentEvaluationSummary(BaseModel):
    """
    특정 학생의 여러 학과에 대한 평가 통계를 간략히 정리해 응답하는 스키마입니다.

    Attributes:
        student_id (int): 학생 식별 학번
        student_name (str): 학생 이름
        total_evaluations (int): 진행된/존재하는 총 평가 개수
        top_departments (List[dict]): 평가 점수나 추천도가 높은 상위 학과 정보
        message (Optional[str]): 종합 요약 메시지
    """
    student_id: int  # changed from int to str
    student_name: str
    total_evaluations: int
    top_departments: List[dict]
    message: Optional[str] = None


# Admin Schemas
class ErrorDetail(BaseModel):
    """
    데이터 업로드/작업 시 발생한 한 건의 에러의 위치와 원인을 담는 스키마입니다.

    Attributes:
        row (int): 에러가 발생한 행(row)의 번호나 인덱스
        item_id (str): 에러가 발생한 데이터의 식별키나 내용 요약
        reason (str): 실패 이유
    """
    row: int
    item_id: str
    reason: str

class DataUploadResponse(BaseModel):
    """
    데이터(CSV 등) 벌크 업로드 후 처리 결과를 나타내는 응답 스키마입니다.

    Attributes:
        success (bool): 완전 성공 혹은 일부/전체 실패 여부
        message (str): 안내 문구
        uploaded_count (int): 신규 추가된 행 개수
        updated_count (int): 기존 데이터로 덮어씌워진(갱신된) 행 개수
        errors (Optional[List[str]]): 전체 에러 로그들의 집합
        detailed_errors (Optional[List[ErrorDetail]]): 상세 구조화된 에러 내역
    """
    success: bool
    message: str
    uploaded_count: int
    updated_count: int
    errors: Optional[List[str]] = None
    detailed_errors: Optional[List[ErrorDetail]] = None


class BulkEvaluationRequest(BaseModel):
    """
    관리자 페이지 등에서 대량의 진단을 한 번에 동기/비동기로 요청하는 스키마입니다.

    Attributes:
        student_ids (Optional[List[int]]): 지정된 특정 학생들의 목록
        department_ids (Optional[List[int]]): 지정된 특정 전공/학과들의 목록
        force_recalculate (bool): 기존에 캐시된 이력이 있어도 강제로 재수행할 지 여부
    """
    student_ids: Optional[List[int]] = None
    department_ids: Optional[List[int]] = None
    force_recalculate: bool = False


class BulkEvaluationResponse(BaseModel):
    """
    대량의 진단 수행 완료 시 해당 성과와 통계를 리턴하는 응답 스키마입니다.

    Attributes:
        success (bool): 요청이 무사히 처리되었는지 여부
        message (str): 처리 안내 문구
        total_students (int): 진단 대상이 된 전체 학생 수
        total_departments (int): 검사해야 할 부서 수
        total_evaluations (int): 두 변수의 조합으로 돌려진 총 판정 개수
        success_count (int): 그 중 성공한 평가 연산 수
        error_count (int): 에러나 예외로 처리 실패한 건 수
        errors (Optional[List[str]]): 실패 에러 요약 내역
    """
    success: bool
    message: str
    total_students: int
    total_departments: int
    total_evaluations: int
    success_count: int
    error_count: int
    errors: Optional[List[str]] = None


class CachedEvaluationStats(BaseModel):
    """
    서버에서 저장(Caching)된 이전 평가 결과들의 통계를 반환하는 스키마입니다.

    Attributes:
        total_cached (int): 총 저장된 캐시 결과 개수
        cached_by_department (dict): 학과명과 결과 개수의 매핑 (예: "CS": 30)
        last_update (Optional[datetime]): 가장 최근 수행된 평가의 시간
    """
    total_cached: int
    cached_by_department: dict  # {department_name: count}
    last_update: Optional[datetime] = None


# 입력 DTO는 uploads 서브모듈로 분리하고 재노출(기존 import 경로 유지)
from models.schemas.uploads import (
    MajorSurveyDataUpload,
    StudentDataUpload,
    EnrollmentDataUpload,
    CurriculumDataUpload,
    RecommendationDataUpload,
    RequirementDataUpload,
    RequirementCourseDataUpload,
    CollegeDataUpload,
    AdvisorDataUpload,
    DepartmentDataUpload,
    CourseDataUpload,
)
