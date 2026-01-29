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
    'A+': 4.5, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
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
# Evaluation System Weights
# ============================================================================

# Weight for Required Courses Score (필수과목 학점 점수)
WEIGHT_REQUIRED_COURSES = 0.40

# Weight for GPA Score (GPA 점수)
WEIGHT_GPA = 0.20

# Weight for Recommended Courses Completion (권장과목 이수 여부)
WEIGHT_RECOMMENDED_COMPLETION = 0.15

# Weight for Recommended Courses Grade (권장과목 학점 점수)
WEIGHT_RECOMMENDED_GRADE = 0.15

# Weight for Curriculum Completion (교육과정 완성도)
WEIGHT_CURRICULUM_COMPLETION = 0.10

# Overall score thresholds for grading
GRADE_THRESHOLDS = {
    'A': 90.0,
    'B': 80.0,
    'C': 70.0,
    'D': 60.0,
    'F': 0.0
}

# Minimum score to satisfy entry requirements
MIN_SATISFACTION_SCORE = 70.0

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
