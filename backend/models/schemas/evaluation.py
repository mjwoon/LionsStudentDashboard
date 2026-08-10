"""
평가/진단 결과 및 업로드/대량평가 결과 스키마. (models/schemas 에서 분리)
"""

from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# Base Response Models

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
