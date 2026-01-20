from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Base Response Models
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
    is_entry_requirement: bool
    is_recommended: bool
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
    is_entry_requirement: bool
    is_retake: bool

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
    per_page: int


class SurveyRoundResponse(BaseModel):
    meta: SurveyRoundMeta
    round_info: RoundInfo
    submissions: List[SurveySubmissionItem]
