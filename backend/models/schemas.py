from pydantic import BaseModel, EmailStr, Field, AliasChoices
from typing import Optional, List, Dict, Any
from datetime import datetime


# Base Response Models
class CollegeBase(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class DepartmentDetail(BaseModel):
    id: int
    code: str
    name: str
    college_name: str
    min_credits: int
    is_evaluation_available: bool = False

    class Config:
        from_attributes = True


class AcademicInfo(BaseModel):
    pride: str
    class_number: int
    track: Optional[str] = None  # 전계열, 자연계열, 인문사회계열
    advisor_id: Optional[int] = None
    advisor_name: Optional[str] = None
    status: str = "재학"
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


# Student Models
class StudentBase(BaseModel):
    student_id: int  # Integer PK
    name: str
    email: EmailStr
    phone: Optional[str] = None


class StudentCreate(StudentBase):
    department_id: int
    advisor_id: Optional[int] = None
    pride: str
    class_number: int


class StudentInList(StudentBase):
    department: DepartmentBase
    academic_info: AcademicInfo
    latest_major_choice: Optional[str] = None  # 최신 희망 학과
    decision_certainty: Optional[int] = None  # 전공결정도 (1-5)
    completion_status: Optional[str] = None  # 이수현황 (예: "15/20")
    course_suitability: Optional[str] = None  # 수강과목 적합성 (예: "양호")

    class Config:
        from_attributes = True


class StudentDetail(StudentBase):
    department: DepartmentBase
    academic_info: AcademicInfo

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    count: int
    page: int
    per_page: int
    students: List[StudentInList]


class StudentCreateResponse(BaseModel):
    message: str
    student_id: int


# Course Models
class CourseFlags(BaseModel):
    is_retake_only: bool


class CourseBase(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    credits: int
    course_type: str


class CourseInList(CourseBase):
    department: DepartmentBase
    flags: CourseFlags
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    count: int
    page: int
    per_page: int
    courses: List[CourseInList]


class CourseEnrollmentDetail(BaseModel):
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

    class Config:
        from_attributes = True


class StudentCoursesResponse(BaseModel):
    student_id: int
    total_credits: int
    course_history: List[CourseEnrollmentDetail]


class EntryRequirementCourse(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    credits: int
    course_type: str
    department_id: int
    department_name: str
    is_recommended: bool

    class Config:
        from_attributes = True


class EntryRequirementsResponse(BaseModel):
    count: int
    courses: List[EntryRequirementCourse]


# Department Models
class DepartmentListResponse(BaseModel):
    count: int
    departments: List[DepartmentDetail]


class DepartmentCurriculum(BaseModel):
    department_name: str
    graduation_min_credits: int
    tracks: List[str]
    entry_requirements_description: str


# Survey Models
class SurveyChoiceBase(BaseModel):
    id: int
    name: str


class SurveyHistoryItem(BaseModel):
    survey_id: int
    round: int
    submitted_at: str
    first_choice: SurveyChoiceBase
    second_choice: Optional[SurveyChoiceBase] = None
    decision_scale: int

    class Config:
        from_attributes = True


class StudentSurveysResponse(BaseModel):
    history: List[SurveyHistoryItem]


class SurveyCreate(BaseModel):
    student_id: int
    first_choice_dept_id: str
    second_choice_dept_id: Optional[str] = None
    survey_round: int
    decision_scale: int


class SurveySubmitData(BaseModel):
    survey_id: int
    submitted_at: str


class SurveyCreateResponse(BaseModel):
    success: bool
    message: str
    data: SurveySubmitData


class MajorPreference(BaseModel):
    dept_name: str
    count: int
    avg_decision_scale: float


class SurveyStatus(BaseModel):
    current_round: int
    participation_rate: float


class SurveyOverview(BaseModel):
    total_students: int
    total_departments: int
    entry_requirement_completion_rate: float


class SurveySummaryResponse(BaseModel):
    overview: SurveyOverview
    major_preferences: List[MajorPreference]
    survey_status: SurveyStatus


class SurveySubmissionItem(BaseModel):
    survey_id: int
    student_id: int
    name: str
    department_name: str
    first_choice: SurveyChoiceBase
    second_choice: Optional[SurveyChoiceBase] = None
    decision_scale: int
    submitted_at: str

    class Config:
        from_attributes = True


class RoundInfo(BaseModel):
    round_id: int
    title: str
    status: str


class SurveyRoundMeta(BaseModel):
    total_count: int
    current_page: int
    total_pages: int
    per_page: int = 20


# Dashboard Statistics Models
class DepartmentWithStats(BaseModel):
    id: str
    name: str
    college: str
    color: str
    students: int
    percent: float

    class Config:
        from_attributes = True


class TrendDataPoint(BaseModel):
    period: str
    data: dict  # department_id: count

    class Config:
        from_attributes = True


class SurveyRoundInfo(BaseModel):
    round_number: int
    title: str
    status: str
    end_date: Optional[str] = None


class SurveyRoundSummary(BaseModel):
    round_number: int
    title: str


class DashboardStatsResponse(BaseModel):
    colleges: List[CollegeBase]
    departments: List[DepartmentWithStats]
    current_data: List[DepartmentWithStats]
    trend_data: List[TrendDataPoint]
    survey_info: Optional[SurveyRoundInfo] = None
    survey_rounds: Optional[List[SurveyRoundSummary]] = None
    current_data_by_round: Optional[Dict[int, List[DepartmentWithStats]]] = None

    class Config:
        from_attributes = True


class SurveyRoundResponse(BaseModel):
    meta: SurveyRoundMeta
    round_info: RoundInfo
    submissions: List[SurveySubmissionItem]


# Department Entry Requirements Models
class RequirementCourseDetail(BaseModel):
    course_code: str
    course_name: str
    credits: int

    class Config:
        from_attributes = True


class DepartmentEntryRequirementDetail(BaseModel):
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

    class Config:
        from_attributes = True


# Student Requirement Status Models
class StudentRequirementStatusDetail(BaseModel):
    id: int
    student_id: int
    department_id: int
    department_name: str
    is_satisfied: bool
    analysis_json: Optional[dict] = None
    ai_summary: Optional[str] = None
    calculated_at: datetime

    class Config:
        from_attributes = True


class StudentRequirementStatusResponse(BaseModel):
    student_id: int
    first_choice_dept_id: Optional[str] = None
    evaluations: List[StudentRequirementStatusDetail]


class MajorEvaluationSummary(BaseModel):
    """전공 평가 요약"""
    required_courses_total: int
    required_courses_completed: int
    required_courses_percentage: float
    missing_courses: List[dict]


class StudentMajorEvaluationResponse(BaseModel):
    """학생 전공 평가 응답"""
    student_id: int
    department_id: int
    department_name: str
    evaluation: MajorEvaluationSummary
    entry_requirements: Optional[str] = None


# Evaluation Service Schemas
class RequiredCoursesResult(BaseModel):
    """필수 과목 평가 결과"""
    score: float
    total_requirements: int
    satisfied_requirements: int
    details: List[dict]
    pass_: bool = None
    message: str

    class Config:
        populate_by_name = True
        fields = {'pass_': 'pass'}


class RecommendedCoursesResult(BaseModel):
    """권장 과목 평가 결과"""
    score: float
    total_courses: int
    completed_courses: int
    total_credits: int
    completed_credits: int
    completion_rate: float
    details: List[dict]
    message: str


class RelatedCreditsResult(BaseModel):
    """관련 학점 평가 결과"""
    score: float
    total_available_credits: int
    earned_credits: int
    message: str
    target_credits: Optional[float] = None


class EvaluationResultResponse(BaseModel):
    """전공진입 적합도 평가 결과"""
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

    class Config:
        from_attributes = True


class BatchEvaluationRequest(BaseModel):
    """배치 평가 요청"""
    department_id: Optional[int] = None
    admission_year: int = 2025
    limit_students: Optional[int] = None


class BatchEvaluationResponse(BaseModel):
    """배치 평가 응답"""
    department_id: int
    department_name: str
    total_students: int
    saved_count: int
    message: str


class StudentEvaluationSummary(BaseModel):
    """학생 평가 요약"""
    student_id: int  # changed from int to str
    student_name: str
    total_evaluations: int
    top_departments: List[dict]
    message: Optional[str] = None


# Admin Schemas
class ErrorDetail(BaseModel):
    row: int
    item_id: str
    reason: str

class DataUploadResponse(BaseModel):
    """데이터 업로드 응답"""
    success: bool
    message: str
    uploaded_count: int
    updated_count: int
    errors: Optional[List[str]] = None
    detailed_errors: Optional[List[ErrorDetail]] = None


class BulkEvaluationRequest(BaseModel):
    """대량 진단 요청"""
    student_ids: Optional[List[int]] = None
    department_ids: Optional[List[int]] = None
    force_recalculate: bool = False


class BulkEvaluationResponse(BaseModel):
    """대량 진단 응답"""
    success: bool
    message: str
    total_students: int
    total_departments: int
    total_evaluations: int
    success_count: int
    error_count: int
    errors: Optional[List[str]] = None


class CachedEvaluationStats(BaseModel):
    """캐시된 진단 결과 통계"""
    total_cached: int
    cached_by_department: dict  # {department_name: count}
    last_update: Optional[datetime] = None


class MajorSurveyDataUpload(BaseModel):
    """희망 전공 조사 데이터 업로드 스키마"""
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID"))
    student_id: int = Field(..., validation_alias=AliasChoices("student_id", "학번"))
    survey_round_id: int = Field(..., validation_alias=AliasChoices("survey_round_id", "survey_round", "회차", "회차ID"))
    first_choice_id: int = Field(..., validation_alias=AliasChoices("first_choice_id", "1지망", "1지망학과", "1지망학과ID", "1지망 학과 ID"))
    second_choice_id: int = Field(..., validation_alias=AliasChoices("second_choice_id", "2지망", "2지망학과", "2지망학과ID", "2지망 학과 ID"))
    decision_status_id: Optional[int] = Field(None, validation_alias=AliasChoices("decision_status_id", "결정상태", "결정상태ID"))
    decision_scale: Optional[int] = Field(None, validation_alias=AliasChoices("decision_scale", "결정척도", "리커트 척도"))

    model_config = {"populate_by_name": True}


class StudentDataUpload(BaseModel):
    """학생 데이터 업로드 스키마"""
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
    """수강 데이터 업로드 스키마 (한국어 CSV 헤더 지원)"""
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
    """교육과정 데이터 업로드 스키마"""
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code", "학과코드", "소속학과", "학과"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID"))
    course_year: int = Field(..., validation_alias=AliasChoices("course_year", "권장학년", "학년", "수강학년"))
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드", "교과목번호"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목명"))
    credits: int = Field(3, validation_alias=AliasChoices("credits", "학점"))
    course_type: Optional[str] = Field(None, validation_alias=AliasChoices("course_type", "이수구분", "구분", "과목구분", "과목유형"))
    semester: int = Field(1, validation_alias=AliasChoices("semester", "권장학기", "학기", "수강학기"))

    model_config = {"populate_by_name": True}


class RecommendationDataUpload(BaseModel):
    """권장과목 데이터 업로드 스키마"""
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID", "권장과목ID"))
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code", "학과코드", "소속학과", "학과"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목 이름", "교과목명"))

    model_config = {"populate_by_name": True}


class RequirementDataUpload(BaseModel):
    """학과 요건 데이터 업로드 스키마"""
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
    """요건 대상 과목 매핑 데이터 업로드 스키마"""
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "ID", "매핑ID"))
    requirement_id: int = Field(..., validation_alias=AliasChoices("requirement_id", "요건 ID", "요건ID"))
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드", "과목번호"))

    model_config = {"populate_by_name": True}


class CollegeDataUpload(BaseModel):
    """대학 데이터 업로드 스키마"""
    id: Optional[int] = None
    name: str


class AdvisorDataUpload(BaseModel):
    """지도교수 데이터 업로드 스키마"""
    id: Optional[int] = Field(None, validation_alias=AliasChoices("id", "교수ID", "ID"))
    name: str = Field(..., validation_alias=AliasChoices("name", "이름", "교수명", "성명"))
    email: Optional[str] = Field(None, validation_alias=AliasChoices("email", "이메일"))
    department_id: Optional[int] = Field(None, validation_alias=AliasChoices("department_id", "소속학과ID", "학과ID"))

    model_config = {"populate_by_name": True}


class DepartmentDataUpload(BaseModel):
    """학과 데이터 업로드 스키마"""
    id: Optional[int] = None
    code: str
    name: str
    college_name: Optional[str] = None  # college name으로 매칭
    college_id: Optional[int] = None  # 또는 college_id 직접 지정
    min_credits: int = 130


class CourseDataUpload(BaseModel):
    """과목 데이터 업로드 스키마 (한국어 CSV 헤더 지원)"""
    course_code: str = Field(..., validation_alias=AliasChoices("course_code", "학수번호", "과목코드"))
    course_name: str = Field(..., validation_alias=AliasChoices("course_name", "과목명", "교과목이름", "교과목 이름", "교과목명"))
    course_type: Optional[str] = Field(None, validation_alias=AliasChoices("course_type", "이수구분"))
    course_year: Optional[int] = Field(None, validation_alias=AliasChoices("course_year", "학년", "권장학년", "권장 학년"))
    semester: Optional[int] = Field(None, validation_alias=AliasChoices("semester", "학기", "권장학기", "권장 학기"))
    department_name: Optional[str] = Field(None, validation_alias=AliasChoices("department_name", "설강학과", "관장학과"))
    department_code: Optional[str] = Field(None, validation_alias=AliasChoices("department_code"))
    credits: Optional[int] = Field(None, validation_alias=AliasChoices("credits", "학점"))
    description: Optional[str] = Field(None, validation_alias=AliasChoices("description", "교과목개요", "개요"))
    prerequisite: Optional[str] = Field(None, validation_alias=AliasChoices("prerequisite", "선수강 과목", "선수과목"))

    model_config = {"populate_by_name": True}
