"""
순수 도메인 점수 로직 — SQLAlchemy Session·Neo4j 드라이버를 알지 못한다.

EvaluationService에서 IO(DB 조회·그래프 접속)와 뒤섞여 있던 '계산' 책임만 떼어내
평범한 데이터 구조로 결정론적으로 동작하는 순수 함수로 만든다.
→ DB/Neo4j 없이 빠른 단위 테스트가 가능해지고(테스트 피라미드 바닥),
   유사도 출처(그래프)는 콜러블로 주입되어 대체(fake) 가능하다(의존성 역전).

동작 보존 주의:
- 그래프 가용성 확인(is_graph_available)은 3단계에서 '지연' 호출된다. 1·2단계에서
  매칭되면 그래프를 건드리지 않는 기존 동작을 지키기 위해 불리언이 아닌 콜러블로 받는다.
"""

from typing import Callable, Dict, List, NamedTuple, Optional, Set, Tuple


class SimilarMatch(NamedTuple):
    """유사과목 판정 결과.

    (accepted, similarity, matched)로 언패킹 가능한 튜플 호환 Value Object.
    기존 `is_similar, sim, match = ...` 언패킹 및 presenter 콜백과 호환된다.
    """
    accepted: bool
    similarity: float
    matched: Optional[Dict]


# (source_course_code, target_course_code) -> 유사도 0.0~1.0
SimilarityFn = Callable[[str, str], float]
# (target_codes, target_name, completed) -> SimilarMatch
MatcherFn = Callable[[Set[str], str, Dict], SimilarMatch]


def find_best_similar_course(
    target_course_codes: Set[str],
    target_course_name: str,
    student_completed_courses: Dict,
    *,
    is_graph_available: Callable[[], bool],
    get_similarity: SimilarityFn,
    threshold: float,
) -> SimilarMatch:
    """학생이 이수한 과목 중 타겟 과목과 가장 유사한 과목 찾기.

    판정 우선순위:
    1. 동일 학수코드     → 유사도 1.0 (항상 최우선)
    2. 과목명 직접 일치  → 유사도 1.0 (그래프 연결 여부와 무관)
    3. 그래프 유사도     → threshold 이상이면 인정 (1·2단계 실패 시에만 지연 조회)
    """
    completed_codes = student_completed_courses["codes"]
    completed_names = student_completed_courses["names"]
    completed_details = student_completed_courses["details"]

    # ── 1단계: 동일 학수코드 (항상 최우선) ──────────────────────────
    for target_code in target_course_codes:
        if target_code in completed_codes:
            for detail in completed_details:
                if detail["course_code"] == target_code:
                    return SimilarMatch(True, 1.0, detail)

    # ── 2단계: 과목명 직접 일치 (그래프 연결 여부와 무관) ────────────
    if target_course_name in completed_names:
        for detail in completed_details:
            if detail["course_name"] == target_course_name:
                return SimilarMatch(True, 1.0, detail)

    # ── 3단계: 그래프 유사도 매칭 (1·2단계에서 미인정된 경우만, 지연 평가) ──
    if is_graph_available():
        best_similarity = 0.0
        best_match = None
        for detail in completed_details:
            for target_code in target_course_codes:
                sim = get_similarity(detail["course_code"], target_code)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = detail
        if best_similarity >= threshold:
            return SimilarMatch(True, best_similarity, best_match)
        return SimilarMatch(False, best_similarity, None)

    return SimilarMatch(False, 0.0, None)


def entry_requirement_score(
    necessary_courses: List[Dict],
    student_completed_courses: Dict,
) -> float:
    """진입요건 충족 점수. 요건이 없으면 100%, 있으면 이수한 필수과목 비율(%)."""
    if not necessary_courses:
        return 100.0

    completed_codes = student_completed_courses["codes"]
    completed_names = student_completed_courses["names"]

    completed_count = 0
    for necessary in necessary_courses:
        course_code = necessary.get("course_code", "")
        course_name = necessary.get("course_name", "")
        # 학수코드 또는 과목명이 일치하면 이수로 인정
        if course_code in completed_codes or course_name in completed_names:
            completed_count += 1

    score = (completed_count / len(necessary_courses)) * 100
    return round(min(100.0, score), 2)


def recommended_courses_score(
    recommended_course_names: List[str],
    student_completed_courses: Dict,
    course_name_to_codes: Dict[str, Set[str]],
    matcher: MatcherFn,
) -> Tuple[float, float]:
    """권장과목 이수 (동일과목 비율, 유사과목 인정 비율). 권장과목 없으면 (100, 100)."""
    if not recommended_course_names:
        return 100.0, 100.0

    completed_codes = student_completed_courses["codes"]
    completed_names = student_completed_courses["names"]

    exact_match_count = 0
    similar_match_count = 0
    for rec_name in recommended_course_names:
        # 동일과목: 과목명 일치 + 학수코드도 일치
        if rec_name in completed_names:
            expected_codes = course_name_to_codes.get(rec_name, set())
            if expected_codes & completed_codes:
                exact_match_count += 1

        # 유사과목: 그래프 유사도 또는 과목명 폴백
        target_codes = course_name_to_codes.get(rec_name, set())
        if matcher(target_codes, rec_name, student_completed_courses).accepted:
            similar_match_count += 1

    total = len(recommended_course_names)
    exact_rate = (exact_match_count / total) * 100
    similar_rate = (similar_match_count / total) * 100
    return round(exact_rate, 2), round(similar_rate, 2)


def curriculum_completion_score(
    first_year_courses: List[Dict],
    student_completed_courses: Dict,
    matcher: MatcherFn,
) -> Tuple[float, float]:
    """교육과정(1학년) 이수 (동일과목 비율, 유사과목 인정 비율). 과목 없으면 (100, 100)."""
    if not first_year_courses:
        return 100.0, 100.0

    completed_codes = student_completed_courses["codes"]

    exact_match_count = 0
    similar_match_count = 0
    for course in first_year_courses:
        course_code = course.get("course_code", "")
        course_name = course.get("course_name", "")

        # 동일과목: 학수코드 일치
        if course_code in completed_codes:
            exact_match_count += 1

        # 유사과목: 그래프 유사도 또는 과목명 폴백
        target_codes = {course_code} if course_code else set()
        if matcher(target_codes, course_name, student_completed_courses).accepted:
            similar_match_count += 1

    total = len(first_year_courses)
    exact_rate = (exact_match_count / total) * 100
    similar_rate = (similar_match_count / total) * 100
    return round(exact_rate, 2), round(similar_rate, 2)
