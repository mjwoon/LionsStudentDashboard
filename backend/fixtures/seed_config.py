"""
Seed data configuration and constants.

This module contains all the configuration data used for seeding the database,
including department IDs, student profiles, and grade distributions.
"""

from typing import List, Tuple, Dict, Any

# ============================================================================
# Department IDs
# ============================================================================

DEPT_LIONS_COLLEGE = 100
DEPT_COMPUTER_SCIENCE = 300
DEPT_DATA_INTELLIGENCE = 303
DEPT_DESIGN_CONVERGENCE = 304
DEPT_ARCHITECTURE = 200
DEPT_ELECTRONICS = 204
DEPT_INDUSTRIAL_ENG = 207
DEPT_INDUSTRIAL_MGMT = 207
DEPT_MOLECULAR_PHARM = 404
DEPT_ADVERTISING_PR = 600

# ============================================================================
# Academic Settings
# ============================================================================

MAX_CREDITS_PER_SEMESTER = 20
TARGET_ADDITIONAL_ENROLLMENTS = 200
REGULAR_STUDENT_COUNT = 30

# ============================================================================
# Grade Options and Weights
# ============================================================================

GRADE_OPTIONS: List[Tuple[str, float]] = [
    ('A+', 4.5), ('A0', 4.0), 
    ('B+', 3.3), ('B0', 3.0), 
    ('C+', 2.3), ('C0', 2.0), 
    ('D+', 1.3), ('D0', 1.0), 
    ('F', 0.0)
]

# Default grade weights for normal distribution (합계: 86)
GRADE_WEIGHTS = [15, 20, 12, 15, 8, 6, 5, 3, 2]

# Grade profile weights
GRADE_PROFILE_WEIGHTS = {
    "excellent": [25, 30, 15, 10, 8, 5, 3, 2, 2],  # A+ 중심
    "average": [5, 8, 15, 20, 15, 10, 8, 5, 2],     # B 중심
    "struggling": [1, 2, 5, 8, 12, 15, 15, 12, 5],  # C-D 중심
    "normal": GRADE_WEIGHTS                          # 기본 분포
}

# ============================================================================
# Special Students Configuration
# ============================================================================
# These students have fixed, reproducible data for consistent testing

SPECIAL_STUDENTS_CONFIG: List[Dict[str, Any]] = [
    {
        "student_id": "2025123001",
        "name": "강우수",  # Excellent student (우수 = excellent)
        "email": "kim.woosoo@hanyang.ac.kr",
        "phone": "010-1111-1111",
        "track": "자연계열",
        "pride": "O",
        "class_number": 6,
        "advisor_id": 2,
        "target_dept": DEPT_DATA_INTELLIGENCE,
        "decision_scale": 5,  # 매우 확실 - 성적 우수, 목표 명확
        "grade_seed": 1001,  # Random seed for reproducible grades
        "grade_profile": "excellent",  # High achiever (mostly A grades)
        "description": "High-performing student with clear career goals in Data Intelligence"
    },
    {
        "student_id": "2025123002",
        "name": "강보통",  # Average student (보통 = average)
        "email": "lee.botong@hanyang.ac.kr",
        "phone": "010-2222-2222",
        "track": "전계열",
        "pride": "S",
        "class_number": 10,
        "advisor_id": 2,
        "target_dept": DEPT_DATA_INTELLIGENCE,
        "decision_scale": 3,  # 보통 - 평범한 성적, 고민 중
        "grade_seed": 2002,  # Random seed for reproducible grades
        "grade_profile": "average",  # Average grades (B range)
        "description": "Average student exploring major options, considering Data Intelligence"
    },
    {
        "student_id": "2025123003",
        "name": "강고민",  # Struggling student (고민 = worry/concern)
        "email": "park.gomin@hanyang.ac.kr",
        "phone": "010-3333-3333",
        "track": "인문사회계열",
        "pride": "O",
        "class_number": 6,
        "advisor_id": 1,
        "target_dept": DEPT_DESIGN_CONVERGENCE,
        "decision_scale": 2,  # 불확실 - 성적 부진, 진로 고민
        "grade_seed": 3003,  # Random seed for reproducible grades
        "grade_profile": "struggling",  # Lower grades (C-D range)
        "description": "Student facing academic challenges, uncertain about major choice"
    },
    {
        "student_id": "2025345123",
        "name": "홍길동",
        "email": "hong.gildong@hanyang.ac.kr",
        "phone": "010-4444-4444",
        "track": "자연계열",
        "pride": "L",
        "class_number": 3,
        "advisor_id": 1,
        "target_dept": DEPT_DATA_INTELLIGENCE,
        "decision_scale": 4,
        "grade_seed": None,
        "grade_profile": None,  # Uses manual_enrollments instead
        "description": "Student with manually specified enrollment history targeting Data Intelligence",
        "manual_enrollments": [
            {"course_code": "CUL7125", "grade": "A0", "numeric_grade": 4.0, "year": 2026, "semester": 1, "completion_type": "교양필수"},
            {"course_code": "CUL7133", "grade": "B+", "numeric_grade": 3.5, "year": 2026, "semester": 1, "completion_type": "교양필수"},
            {"course_code": "GEN0063", "grade": "B0", "numeric_grade": 3.0, "year": 2026, "semester": 1, "completion_type": "전공기초"},
            {"course_code": "GEN2052", "grade": "C+", "numeric_grade": 2.5, "year": 2026, "semester": 1, "completion_type": "전공기초"},
            {"course_code": "INE1014", "grade": "A0", "numeric_grade": 4.0, "year": 2026, "semester": 1, "completion_type": "전공기초"},
            {"course_code": "VCC1001", "grade": "P", "numeric_grade": 0.0, "year": 2026, "semester": 1, "completion_type": "교양필수"},
            {"course_code": "AIX0004", "grade": "A0", "numeric_grade": 4.0, "year": 2026, "semester": 1, "completion_type": "교양선택"},
            {"course_code": "CLU1073", "grade": "A+", "numeric_grade": 4.5, "year": 2026, "semester": 1, "completion_type": "교양선택"},
            # 2학기 수강 중 (성적 미부여)
            {"course_code": "ICT1001", "grade": None, "numeric_grade": None, "year": 2026, "semester": 2, "completion_type": "전공기초"},
            {"course_code": "MCD1001", "grade": None, "numeric_grade": None, "year": 2026, "semester": 2, "completion_type": "전공핵심"},
            {"course_code": "MMT2012", "grade": None, "numeric_grade": None, "year": 2026, "semester": 2, "completion_type": "전공핵심"},
            {"course_code": "CUL2100", "grade": None, "numeric_grade": None, "year": 2026, "semester": 2, "completion_type": "교양필수"},
            {"course_code": "CSE2010", "grade": None, "numeric_grade": None, "year": 2026, "semester": 2, "completion_type": "전공기초"},
            {"course_code": "MMT4017", "grade": None, "numeric_grade": None, "year": 2026, "semester": 2, "completion_type": "전공핵심"},
        ],
    },
]

# ============================================================================
# Advisor Data
# ============================================================================

ADVISORS_DATA: List[Dict[str, Any]] = [
    # 라이언스 칼리지
    {"id": 1, "name": "박교수", "email": "park@hanyang.ac.kr", "department_id": "100"},
    {"id": 2, "name": "최교수", "email": "choi@hanyang.ac.kr", "department_id": "100"},
    {"id": 3, "name": "김교수", "email": "kim@hanyang.ac.kr", "department_id": "100"},
    # 공과대학
    {"id": 4, "name": "이교수", "email": "lee.ee@hanyang.ac.kr", "department_id": "205"},
    {"id": 5, "name": "정교수", "email": "jung.me@hanyang.ac.kr", "department_id": "206"},
    {"id": 6, "name": "강교수", "email": "kang.chem@hanyang.ac.kr", "department_id": "207"},
    # 소프트웨어융합대학
    {"id": 7, "name": "송교수", "email": "song.cs@hanyang.ac.kr", "department_id": "300"},
    {"id": 8, "name": "윤교수", "email": "yoon.math@hanyang.ac.kr", "department_id": "306"},
    # 첨단융합대학
    {"id": 9, "name": "한교수", "email": "han.semi@hanyang.ac.kr", "department_id": "400"},
    {"id": 10, "name": "오교수", "email": "oh.bio@hanyang.ac.kr", "department_id": "403"},
    # 경상대학
    {"id": 11, "name": "서교수", "email": "seo.biz@hanyang.ac.kr", "department_id": "500"},
    # 글로벌문화통상대학
    {"id": 12, "name": "안교수", "email": "ahn.global@hanyang.ac.kr", "department_id": "700"},
]

# ============================================================================
# College Data
# ============================================================================

COLLEGES_DATA: List[Dict[str, Any]] = [
    {"id": 1, "name": "라이언스 칼리지"},
    {"id": 2, "name": "공학대학"},
    {"id": 3, "name": "소프트웨어융합대학"},
    {"id": 4, "name": "첨단융합대학"},
    {"id": 5, "name": "경상대학"},
    {"id": 6, "name": "커뮤니케이션%컬쳐대학"},
    {"id": 7, "name": "글로벌문화통상대학"},
    {"id": 8, "name": "디자인대학"},
]

# ============================================================================
# Database Connection Settings
# ============================================================================

DB_MAX_RETRIES = 30
DB_RETRY_DELAY = 1  # seconds
