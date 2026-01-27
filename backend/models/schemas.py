from pydantic import BaseModel, EmailStr
from typing import Optional, List
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
    homepage_url: Optional[str] = None

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
    student_id: str
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
    student_id: str


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
    student_id: str
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
    student_id: str
    first_choice_dept_id: int
    second_choice_dept_id: Optional[int] = None
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
    student_id: str
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


class DashboardStatsResponse(BaseModel):
    colleges: List[CollegeBase]
    departments: List[DepartmentWithStats]
    current_data: List[DepartmentWithStats]
    trend_data: List[TrendDataPoint]

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
    student_id: str
    department_id: int
    department_name: str
    is_satisfied: bool
    analysis_json: Optional[dict] = None
    ai_summary: Optional[str] = None
    calculated_at: datetime

    class Config:
        from_attributes = True


class StudentRequirementStatusResponse(BaseModel):
    student_id: str
    first_choice_dept_id: Optional[int] = None
    evaluations: List[StudentRequirementStatusDetail]


class MajorEvaluationSummary(BaseModel):
    """전공 평가 요약"""
    required_courses_total: int
    required_courses_completed: int
    required_courses_percentage: float
    missing_courses: List[dict]


class StudentMajorEvaluationResponse(BaseModel):
    """학생 전공 평가 응답"""
    student_id: str
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
    student_id: str
    student_name: str
    total_evaluations: int
    top_departments: List[dict]
    message: Optional[str] = None
