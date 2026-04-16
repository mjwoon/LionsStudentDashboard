"""
교과목 그래프 API 라우터
Neo4j 기반 교과목 유사도 분석 및 추천 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from services.graph_service import CourseGraphService

router = APIRouter(
    prefix="/graph",
    tags=["Graph Analysis - 교과목 그래프 분석"]
)

# ==================== Pydantic 모델 ====================

class CourseBase(BaseModel):
    """교과목 기본 정보"""
    name: str
    code: str
    category: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[int] = None
    description: Optional[str] = None


class SimilarCourse(CourseBase):
    """유사 교과목 정보 (유사도 포함)"""
    similarity: float


class RecommendedCourse(CourseBase):
    """추천 교과목 정보"""
    avg_similarity: Optional[float] = None
    common_connections: Optional[int] = None
    connections: Optional[int] = None


class CentralCourse(BaseModel):
    """중심성 높은 교과목"""
    name: str
    code: str
    category: Optional[str] = None
    department: Optional[str] = None
    connections: int


class CourseCommunity(BaseModel):
    """교과목 클러스터"""
    course_name: str
    code: str
    department: Optional[str] = None
    similar_courses: List[str]
    cluster_size: int


class CoursePath(BaseModel):
    """교과목 간 경로"""
    course_path: List[str]
    similarities: List[float]
    path_length: int


class CurriculumStructure(BaseModel):
    """교과과정 구조"""
    department: str
    total_courses: int
    total_credits: Optional[float] = None
    avg_credits: float
    categories: List[dict]


class GraphStatistics(BaseModel):
    """그래프 통계"""
    num_courses: int
    num_similarity_edges: int
    num_identical_edges: int
    avg_similarity: float


class MultiCourseRequest(BaseModel):
    """복수 교과목 기반 추천 요청"""
    taken_courses: List[str] = Field(..., description="이미 수강한 교과목 이름 리스트")
    top_k: int = Field(default=10, ge=1, le=50, description="추천 개수")


class HealthResponse(BaseModel):
    """연결 상태 응답"""
    status: str
    connected: bool
    message: str


class PrerequisiteCourse(BaseModel):
    """선수강 과목 정보 (REQUIRES 관계)"""
    name: str
    code: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    credits: Optional[int] = None
    raw_text: Optional[str] = None          # CSV 원본 선수강 텍스트
    match_confidence: Optional[float] = None  # 매핑 신뢰도 (1.0=완전 일치)


class LearningPathEntry(BaseModel):
    """선수강 체인 경로 단건"""
    path_names: List[str]   # [시작과목, ..., 목표과목] 순서
    depth: int              # 선수강 단계 수


# ==================== 상태 확인 ====================

@router.get("/health", response_model=HealthResponse, summary="Neo4j 연결 상태 확인")
def check_graph_health():
    """Neo4j 그래프 데이터베이스 연결 상태를 확인합니다."""
    connected = CourseGraphService.check_connection()
    return {
        "status": "healthy" if connected else "unhealthy",
        "connected": connected,
        "message": "Neo4j 연결 정상" if connected else "Neo4j 연결 실패"
    }


@router.get("/statistics", response_model=GraphStatistics, summary="그래프 통계 조회")
def get_graph_statistics():
    """그래프 전체 통계를 조회합니다."""
    try:
        return CourseGraphService.get_graph_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


# ==================== 교과목 검색 ====================

@router.get("/courses/search", response_model=List[dict], summary="교과목 검색")
def search_courses(
    keyword: str = Query(..., min_length=1, description="검색 키워드"),
    category: Optional[str] = Query(None, description="이수구분 필터"),
    department: Optional[str] = Query(None, description="학과 필터"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수 제한")
):
    """키워드로 교과목을 검색합니다."""
    try:
        return CourseGraphService.search_courses(keyword, category, department, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


@router.get("/courses/code/{code}", summary="학수번호로 교과목 조회")
def get_course_by_code(code: str):
    """학수번호로 특정 교과목을 조회합니다."""
    try:
        course = CourseGraphService.get_course_by_code(code)
        if not course:
            raise HTTPException(status_code=404, detail=f"교과목을 찾을 수 없습니다: {code}")
        return course
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


@router.get("/courses/name/{name}", summary="교과목명으로 조회")
def get_course_by_name(name: str):
    """교과목 이름으로 특정 교과목을 조회합니다."""
    try:
        course = CourseGraphService.get_course_by_name(name)
        if not course:
            raise HTTPException(status_code=404, detail=f"교과목을 찾을 수 없습니다: {name}")
        return course
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


# ==================== 유사 교과목 추천 ====================

@router.get("/recommend/similar/{course_name}", response_model=List[SimilarCourse], 
            summary="유사 교과목 추천")
def get_similar_courses(
    course_name: str,
    top_k: int = Query(10, ge=1, le=50, description="추천 개수"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="최소 유사도")
):
    """특정 교과목과 유사한 교과목을 추천합니다."""
    try:
        courses = CourseGraphService.get_similar_courses(course_name, top_k, min_similarity)
        if not courses:
            raise HTTPException(status_code=404, 
                detail=f"'{course_name}' 교과목을 찾을 수 없거나 유사 교과목이 없습니다.")
        return courses
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {str(e)}")


@router.get("/recommend/similar-by-code/{course_code}", response_model=List[SimilarCourse],
            summary="학수번호로 유사 교과목 추천")
def get_similar_courses_by_code(
    course_code: str,
    top_k: int = Query(10, ge=1, le=50, description="추천 개수"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="최소 유사도")
):
    """학수번호로 유사한 교과목을 추천합니다."""
    try:
        courses = CourseGraphService.get_similar_courses_by_code(course_code, top_k, min_similarity)
        if not courses:
            raise HTTPException(status_code=404,
                detail=f"학수번호 '{course_code}'를 찾을 수 없거나 유사 교과목이 없습니다.")
        return courses
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {str(e)}")


@router.post("/recommend/multiple", response_model=List[RecommendedCourse],
             summary="복수 교과목 기반 추천")
def recommend_by_multiple_courses(request: MultiCourseRequest):
    """
    여러 교과목을 수강한 학생에게 다음 교과목을 추천합니다.
    이미 수강한 교과목과의 유사도를 종합하여 추천합니다.
    """
    try:
        if not request.taken_courses:
            raise HTTPException(status_code=400, detail="수강한 교과목 목록이 필요합니다.")
        return CourseGraphService.recommend_by_multiple_courses(
            request.taken_courses, request.top_k
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {str(e)}")


@router.get("/recommend/department/{department}", response_model=List[RecommendedCourse],
            summary="학과별 교과목 추천")
def recommend_by_department(
    department: str,
    taken_courses: Optional[str] = Query(None, description="수강한 교과목 (쉼표로 구분)"),
    top_k: int = Query(10, ge=1, le=50, description="추천 개수")
):
    """특정 학과의 인기 교과목을 추천합니다."""
    try:
        taken_list = [c.strip() for c in taken_courses.split(",")] if taken_courses else None
        return CourseGraphService.recommend_by_department(department, taken_list, top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {str(e)}")


# ==================== 그래프 분석 ====================

@router.get("/analysis/centrality", response_model=List[CentralCourse],
            summary="연결 중심성 분석")
def get_degree_centrality(
    top_k: int = Query(20, ge=1, le=100, description="상위 k개")
):
    """가장 많은 교과목과 연결된 교과목을 조회합니다 (연결 중심성)."""
    try:
        return CourseGraphService.get_degree_centrality(top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.get("/analysis/communities", response_model=List[CourseCommunity],
            summary="교과목 클러스터 탐지")
def get_course_communities(
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="최소 유사도"),
    min_cluster_size: int = Query(3, ge=2, le=20, description="최소 클러스터 크기")
):
    """유사도 기반 교과목 클러스터(커뮤니티)를 탐지합니다."""
    try:
        return CourseGraphService.get_course_communities(similarity_threshold, min_cluster_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.get("/analysis/path", response_model=CoursePath, summary="교과목 간 경로 탐색")
def get_course_path(
    start: str = Query(..., description="시작 교과목 이름"),
    end: str = Query(..., description="목표 교과목 이름"),
    max_hops: int = Query(3, ge=1, le=5, description="최대 홉 수")
):
    """두 교과목 간의 유사도 경로를 찾습니다."""
    try:
        path = CourseGraphService.get_course_path(start, end, max_hops)
        if not path:
            raise HTTPException(status_code=404,
                detail=f"'{start}'와 '{end}' 사이의 경로를 찾을 수 없습니다.")
        return path
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"경로 탐색 실패: {str(e)}")


# ==================== 학수번호 기반 분석 ====================

@router.get("/identical/{course_name}", response_model=List[dict],
            summary="동일 학수번호 교과목 조회")
def get_identical_id_courses(course_name: str):
    """동일한 학수번호를 가진 다른 학과의 교과목을 조회합니다."""
    try:
        return CourseGraphService.get_identical_id_courses(course_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


@router.get("/shared-courses", response_model=List[dict], summary="공유 학수번호 통계")
def get_shared_course_ids(
    top_k: int = Query(20, ge=1, le=100, description="상위 k개")
):
    """여러 학과에서 공유하는 학수번호 통계를 조회합니다."""
    try:
        return CourseGraphService.get_shared_course_ids(top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


# ==================== 교과과정 분석 ====================

@router.get("/curriculum", response_model=CurriculumStructure, summary="교과과정 구조 분석")
def get_curriculum_structure(
    department: Optional[str] = Query(None, description="분석할 학과 (미입력시 전체)")
):
    """교과과정 구조를 분석합니다."""
    try:
        return CourseGraphService.get_curriculum_structure(department)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.get("/departments", response_model=List[str], summary="학과 목록 조회")
def get_departments():
    """모든 학과 목록을 조회합니다."""
    try:
        return CourseGraphService.get_departments()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


@router.get("/categories", response_model=List[str], summary="이수구분 목록 조회")
def get_categories():
    """모든 이수구분 목록을 조회합니다."""
    try:
        return CourseGraphService.get_categories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


# ==================== 선수강 관계 (REQUIRES) ====================

@router.get(
    "/prerequisites/{course_name}",
    response_model=List[PrerequisiteCourse],
    summary="선수강 과목 조회",
)
def get_prerequisites(course_name: str):
    """
    특정 교과목의 직접 선수강 과목 목록을 조회합니다.

    graphDB 파이프라인에서 구성된 REQUIRES 관계를 기반으로 합니다.
    - **raw_text**: CSV에 기재된 원본 선수강 과목 텍스트
    - **match_confidence**: 텍스트 매핑 신뢰도 (1.0 = 완전 일치, 0.6 이상 = 의미 매칭)
    """
    try:
        return CourseGraphService.get_prerequisites(course_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"선수강 과목 조회 실패: {str(e)}")


@router.get(
    "/learning-path/{course_name}",
    response_model=List[LearningPathEntry],
    summary="선수강 체인 탐색",
)
def get_learning_path(
    course_name: str,
    max_depth: int = Query(3, ge=1, le=5, description="최대 선수강 체인 깊이 (1~5)"),
):
    """
    특정 교과목을 수강하기 위한 선수강 체인(학습 경로)을 탐색합니다.

    REQUIRES 관계를 재귀적으로 따라가며 목표 과목을 이수하기 위해
    미리 완료해야 하는 과목들의 모든 경로를 반환합니다.

    예: '고급알고리즘' 조회 시 → ['자료구조', '알고리즘', '고급알고리즘'] 경로 반환
    """
    try:
        paths = CourseGraphService.get_learning_path(course_name, max_depth)
        if not paths:
            raise HTTPException(
                status_code=404,
                detail=f"'{course_name}'의 선수강 체인을 찾을 수 없습니다."
            )
        return paths
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"선수강 체인 탐색 실패: {str(e)}")

