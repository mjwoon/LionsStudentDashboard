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

from lions_core.constants import classify_grade


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


def entry_requirement_breakdown(
    groups: List[Dict],
    student_completed_courses: Dict,
) -> Dict:
    """진입요건 규칙 분해 — 최고 진행 그룹 기준(표시와 점수 일관용).

    각 그룹: 후보과목 중 numeric_grade >= target_min 인 이수과목 수가
    required_count 이상이면 100%, 아니면 min(자격수/required_count, 1)*100.
    모든 그룹은 OR 관계이므로 진행률이 가장 높은 그룹을 대표로 삼는다.

    Returns:
        {
          "score": 최고 그룹 진행률(0~100, round2),
          "required": 그 그룹의 required_count,
          "qualifying": 그 그룹의 자격 이수 과목수(required로 clamp, 표시용),
          "attempted": 그 그룹의 후보과목 중 성적과 무관하게 이수한 과목수,
          "satisfied": score >= 100,
          "has_requirement": 그룹 존재 여부,
        }
        그룹이 없으면 score=100, has_requirement=False.

    attempted가 필요한 이유: qualifying만 세면 '아직 안 들은 학생'과 '들었는데 성적이
    모자란 학생'이 똑같이 0으로 떨어진다. 이 시스템의 대상은 2학년 진입을 준비하는
    1학년이라 요건 과목 미이수가 정상 상태다. 둘을 구분해야 '진행 전'과 '차단'을
    가를 수 있다(entry_gate_state 참고).
    """
    if not groups:
        return {
            "score": 100.0,
            "required": 0,
            "qualifying": 0,
            "attempted": 0,
            "satisfied": True,
            "has_requirement": False,
        }

    completed_numeric = {
        d["course_code"]: (d.get("numeric_grade") or 0.0)
        for d in student_completed_courses["details"]
    }

    best_progress = -1.0
    best_required = 0
    best_qualifying = 0
    best_attempted = 0
    for group in groups:
        required = group["required_count"]
        qualifying = sum(
            1
            for code in group["candidate_codes"]
            if completed_numeric.get(code, 0.0) >= group["target_min"]
        )
        # 성적과 무관하게 '이수 이력이 있는' 후보 과목 수.
        attempted = sum(1 for code in group["candidate_codes"] if code in completed_numeric)
        progress = 100.0 if required <= 0 else min(qualifying / required, 1.0) * 100
        if progress > best_progress:
            best_progress = progress
            best_required = required
            best_qualifying = min(qualifying, required) if required > 0 else qualifying
            best_attempted = min(attempted, required) if required > 0 else attempted

    score = round(best_progress, 2)
    return {
        "score": score,
        "required": best_required,
        "qualifying": best_qualifying,
        "attempted": best_attempted,
        "satisfied": score >= 100.0,
        "has_requirement": True,
    }


def entry_requirement_score_by_rules(
    groups: List[Dict],
    student_completed_courses: Dict,
) -> float:
    """진입요건 부분 점수 (0~100). entry_requirement_breakdown의 score(단일 진실)."""
    return entry_requirement_breakdown(groups, student_completed_courses)["score"]


def weighted_overall_score(
    components: Dict[str, Tuple[float, bool]],
    weights: Dict[str, float],
) -> float:
    """존재하는 항목만으로 가중 평균 — 없는 항목의 가중치는 재정규화로 흡수한다.

    배경: 요건·권장 데이터가 등록되지 않은 학과는 해당 항목이 공허참 100%로
    채워진다. 이를 그대로 가중합하면 데이터 공백이 곧 가산점이 되어
    (0.4 + 0.3) × 100 = 70점이 바닥으로 깔린다. '평가할 근거가 없다'와
    '완벽히 충족했다'는 다르므로, 근거 없는 항목은 분자·분모 모두에서 뺀다.

    Args:
        components: {항목명: (점수 0~100, 데이터 존재 여부)}
        weights: {항목명: 가중치}. components에 없는 키는 무시된다.

    Returns:
        존재 항목의 가중 평균(0~100, round2). 존재 항목이 없으면 0.0.
    """
    present = {
        name: score
        for name, (score, has_data) in components.items()
        if has_data and weights.get(name, 0.0) > 0
    }
    total_weight = sum(weights[name] for name in present)
    if total_weight <= 0:
        return 0.0

    weighted_sum = sum(present[name] * weights[name] for name in present)
    return round(weighted_sum / total_weight, 2)


def build_overall_components(
    entry_breakdown: Dict,
    recommended_similar_rate: float,
    recommended_total: int,
    curriculum_similar_rate: float,
    curriculum_total: int,
) -> Dict[str, Tuple[float, bool]]:
    """종합 점수 입력 조립 — 항목별 (점수, 데이터 존재 여부).

    서비스와 프레젠터가 같은 종합 점수를 내도록 조립 규칙을 한 곳에 둔다(단일 진실).
    '데이터 존재 여부'는 각 항목의 평가 근거(요건 그룹/권장과목/1학년 과목)가
    실제로 등록되어 있는지를 뜻한다.
    """
    return {
        "entry_requirement": (
            entry_breakdown["score"],
            bool(entry_breakdown.get("has_requirement", False)),
        ),
        "recommended_courses": (recommended_similar_rate, recommended_total > 0),
        "curriculum_completion": (curriculum_similar_rate, curriculum_total > 0),
    }


def is_evaluable(components: Dict[str, Tuple[float, bool]]) -> bool:
    """평가 근거가 하나라도 있는가 — 없으면 점수 자체를 제시하면 안 된다.

    근거가 0개인 학과는 어떤 학생을 넣어도 같은 값이 나온다(과거 만점, 지금 0점).
    상수는 학생을 구분하지 못하므로 '0점'이 아니라 '평가 불가'로 다뤄야 하고,
    학과 추천 정렬에서도 빠져야 한다.
    """
    return any(has_data for _, has_data in components.values())


# ── 진입요건 게이트 ────────────────────────────────────────────────
#
# 진입요건은 '얼마나 준비됐나'와 성질이 다르다. 학칙이 정하는 관문(통과/불통과)이지
# 가중치 30~40%짜리 연속값이 아니다. 가중합에 섞으면 다음 역전이 생긴다:
#
#   요건 완전 미충족 (0, 100, 100) -> 0.4*0   + 0.3*100 + 0.3*100 = 60점 (D)
#   요건 완전 충족   (100, 0,  0)  -> 0.4*100 + 0.3*0   + 0.3*0   = 40점 (F)
#
# 임계값을 어디로 옮겨도 사라지지 않는다. 점수는 준비도로 그대로 두되(요건 진행률까지
# 담고 있어 정보 손실이 없다), 등급과 순위는 게이트가 지배하게 한다.

GATE_OPEN = "open"          # 요건 충족 — 진입 가능
GATE_PENDING = "pending"    # 요건 과목 미이수 — 아직 진행 전(1학년의 정상 상태)
GATE_BLOCKED = "blocked"    # 요건 과목을 들었으나 성적 미달 — 실제로 막힘
GATE_UNKNOWN = "unknown"    # 요건 미등록 — 판정할 근거가 없음

# 순위에서의 게이트 우선순위.
# pending은 아직 기회가 열려 있으므로 unknown보다 앞, blocked는 확인된 미달이라 맨 뒤.
# '알 수 없음'은 확인된 미달보다는 앞에 둔다 — 데이터가 없다는 이유로 실제 미달보다
# 불리해질 이유가 없다.
_GATE_RANK = {GATE_OPEN: 3, GATE_PENDING: 2, GATE_UNKNOWN: 1, GATE_BLOCKED: 0}


def entry_gate_state(entry_breakdown: Dict) -> str:
    """진입요건 관문 상태 — open / pending / blocked / unknown.

    '아직 안 들었다'와 '들었는데 성적이 모자란다'를 가른다. 대상이 2학년 진입을
    준비하는 1학년이라 미이수는 정상 상태이고, 이를 차단으로 취급하면 대부분의
    학생이 등급 없이 표시된다.
    """
    if not entry_breakdown.get("has_requirement", False):
        return GATE_UNKNOWN
    if entry_breakdown.get("satisfied", False):
        return GATE_OPEN
    if entry_breakdown.get("attempted", 0) >= entry_breakdown.get("required", 0):
        return GATE_BLOCKED
    return GATE_PENDING


def grade_for(gate_state: str, readiness_score: Optional[float]) -> Optional[str]:
    """준비도 등급. 관문이 확인된 미달(blocked)일 때만 등급을 주지 않는다.

    등급은 '진입 가능성'의 요약이므로 확인된 미달에는 붙을 수 없다. 다만 pending
    (아직 미이수)과 unknown(요건 미등록)까지 막으면 1학년 대부분과 요건 미등록
    학과가 전부 빈칸이 되므로, 이 둘은 blocked와 구분한다.
    """
    if gate_state == GATE_BLOCKED or readiness_score is None:
        return None
    return classify_grade(readiness_score)


def ranking_key(gate_state: str, readiness_score: Optional[float]) -> Tuple[int, float]:
    """학과 추천 정렬 키 — 게이트가 점수를 지배한다.

    (게이트 우선순위, 준비도)의 사전식 비교라 미충족 60점이 충족 40점을 이길 수 없다.
    """
    return (_GATE_RANK.get(gate_state, 0), readiness_score if readiness_score is not None else -1.0)
