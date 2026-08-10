"""
Application-wide constants for the Lions Student Dashboard backend.
"""

# ============================================================================
# Grade System Constants
# ============================================================================

# Failing grade identifier
FAILING_GRADE = 'F'

# Maximum GPA on the scale
MAX_GPA = 4.5

# Grade to numeric value mapping
GRADE_TO_NUMERIC = {
    'A+': 4.5, 'A': 4.0, 
    'B+': 3.3, 'B': 3.0,
    'C+': 2.3, 'C': 2.0,
    'D+': 1.3, 'D': 1.0,
    'F': 0.0
}

# Minimum numeric grades for grade levels (Enum values as keys)
GRADE_LEVEL_MINIMUM = {
    'A': 4.0,
    'B': 3.0,
    'C': 2.0,
    'D': 1.0,
    'F': 0.0
}

# ============================================================================
# Evaluation System Weights (SSOT)
# ============================================================================

# 종합 점수 가중치의 단일 진실 원천(SSOT).
# analysis_json의 overall.weights로도 노출되는 API 계약값이므로 키 이름까지 고정한다.
# (동작 보존: 현재 실제 사용 중인 가중치 그대로. 값 자체의 조정 여부는 별도 트랙에서 결정.)
EVALUATION_WEIGHTS = {
    "entry_requirement": 0.4,      # 진입요건 충족
    "recommended_courses": 0.3,    # 권장과목 유사 이수
    "curriculum_completion": 0.3,  # 교육과정(1학년) 유사 이수
}

# 유사과목 인정 최소 유사도 (Neo4j SIMILAR_TO). 평가 서비스 전용 임계값.
SIMILARITY_THRESHOLD = 0.7

# Overall score thresholds for grading
GRADE_THRESHOLDS = {
    'A': 90.0,
    'B': 80.0,
    'C': 70.0,
    'D': 60.0,
    'F': 0.0
}


def classify_grade(score) -> str:
    """종합 점수를 등급(A~F)으로 판정. GRADE_THRESHOLDS가 유일한 기준(SSOT)."""
    for grade in ('A', 'B', 'C', 'D'):
        if score >= GRADE_THRESHOLDS[grade]:
            return grade
    return 'F'

# Minimum score to satisfy entry requirements
MIN_SATISFACTION_SCORE = 70.0

# ============================================================================
# Organization Constants
# ============================================================================

# 라이언스 칼리지 학과 id. 평가 대상 학과(id > LIONS_COLLEGE_ID)와 라이언스 칼리지
# 소속 학생(department_id == LIONS_COLLEGE_ID)을 구분하는 기준으로 사용된다.
LIONS_COLLEGE_ID = 100


# ============================================================================
# Course System Constants
# ============================================================================

# Course year for first-year curriculum evaluation
FIRST_YEAR = 1

# Default credits if course credits not found
DEFAULT_CREDITS = 3

# ============================================================================
# Logging Configuration
# ============================================================================

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Date format for logs
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
