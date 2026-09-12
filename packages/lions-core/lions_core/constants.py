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

# ============================================================================
# 합성(더미) 데이터 표식
# ============================================================================

# scripts/generate_dummy_requirements.py가 만든 행의 requirement_text 접두어.
# 이 표식이 유일한 식별 수단이다 — 생성 데이터와 원본이 같은 CSV에 병합돼 있고,
# requirement_text는 API 응답에도 화면에도 실리지 않기 때문이다. 운영 환경의
# 업로드 차단(routers/admin_upload_grouped)과 기동 시 탐지(db_migrations)가
# 같은 값을 봐야 하므로 여기에 둔다.
DUMMY_DATA_MARKER = "[더미]"


def is_dummy_requirement_text(text) -> bool:
    """합성 데이터로 표시된 요건 설명인가."""
    return isinstance(text, str) and text.lstrip().startswith(DUMMY_DATA_MARKER)


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

# 라이언스 칼리지의 colleges.id.
#
# 이 단과대학에는 학과가 3개 있다 — 전계열(100)·인문사회계열(101)·자연계열(102).
# 셋 다 학생의 '소속'이지 '진입 대상 전공'이 아니므로 학과 추천에서 제외되고,
# 세 계열의 학생은 모두 라이언스 칼리지 소속으로 취급된다.
#
# 과거에는 이 상수가 학과 id 100을 담고 있었다(이름은 college인데 값은 department).
# 그 탓에 `Department.id > 100`이 101·102를 학과 추천 목록에 흘려보냈고,
# `Student.department_id == 100`은 101·102 소속 학생을 배치 평가에서 누락시켰다.
# 판정 기준은 개별 학과 id가 아니라 단과대학이다.
LIONS_COLLEGE_ID = 1


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
