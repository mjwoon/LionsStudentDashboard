import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.evaluation_service import EvaluationService
from models.models import (
    Student, Department, StudentCourse, Course,
    DepartmentEntryRequirement, RequirementCourse, Curriculum, CourseRecommendation
)

@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy Session"""
    return MagicMock()

@pytest.fixture
def evaluation_service(mock_db_session):
    service = EvaluationService(db=mock_db_session)
    # Neo4j 그래프 의존성 제거
    service._is_graph_available = MagicMock(return_value=False)
    # DB 저장을 막기 위해 _save_evaluation_result 목 처리 
    # (테스트에서 save_to_db 플래그도 끌 것이지만 보험용)
    service._save_evaluation_result = MagicMock()
    return service

def test_evaluate_student_success(evaluation_service, mock_db_session):
    """학생 평가 정상 작동(요건 충족) 시나리오 검증"""
    
    # 설정 데이터
    student_id = 20260001
    department_id = 1
    
    # 학생 Mock
    mock_student = Student(student_id=student_id, name="테스터", department_id=101)
    
    # 학과 Mock
    mock_department = Department(id=department_id, name="컴퓨터학부")
    
    # 수강 이력 Mock
    mock_enrollment = StudentCourse(
        student_id=student_id, course_code="CSE101", grade="A+", year=2026, semester=1
    )
    
    # 과목 Mock
    mock_course = Course(course_code="CSE101", course_name="컴퓨터공학개론", credits=3)

    # _get_department_courses 등 내부 조회 메서드를 목(Mock)으로 감싸기
    evaluation_service._get_student_completed_courses = MagicMock(return_value={
        "codes": {"CSE101"},
        "names": {"컴퓨터공학개론"},
        "details": [{"course_code": "CSE101", "course_name": "컴퓨터공학개론", "grade": "A+", "credits": 3}]
    })

    evaluation_service._get_department_courses = MagicMock(return_value={
        "necessary_courses": [{"course_code": "CSE101", "course_name": "컴퓨터공학개론"}],
        "recommended_courses": ["이산수학"]
    })

    evaluation_service._get_department_first_year_curriculum = MagicMock(return_value=[
        {"course_code": "CSE101", "course_name": "컴퓨터공학개론"},
        {"course_code": "CSE102", "course_name": "프로그래밍기초"}
    ])

    evaluation_service._get_all_course_codes_by_name = MagicMock(return_value={
        "컴퓨터공학개론": {"CSE101"},
        "프로그래밍기초": {"CSE102"},
        "이산수학": {"CSE201"}
    })
    
    # DB 쿼리 체이닝 모방
    # session.query(Model).filter(...).all() / first() 등을 단순히 하기 위해 
    # evaluate_student 내부에서 필요한 쿼리만 오버라이딩
    
    def side_effect_query(model):
        query_mock = MagicMock()
        if model == Student:
            query_mock.filter.return_value.first.return_value = mock_student
        elif model == Department:
            query_mock.filter.return_value.first.return_value = mock_department
        elif model == StudentCourse:
            query_mock.filter.return_value.all.return_value = [mock_enrollment]
        return query_mock

    mock_db_session.query.side_effect = side_effect_query

    # 실행
    result = evaluation_service.evaluate_student(
        student_id=student_id,
        department_id=department_id,
        save_to_db=False
    )
    
    # 검증 - 진입요건 100% 충족 (필수 1개 중 1개 100%)
    assert result['student_id'] == student_id
    assert result['department_name'] == "컴퓨터학부"
    assert result['entry_requirement_score'] == 100.0
    
    # 권장과목 이수율 검증 - 0% (이산수학 안들음)
    assert result['recommended_exact_rate'] == 0.0
    
    # 교육과정 이수율 검증 - 50% (2과목 중 1개 이수)
    assert result['curriculum_exact_rate'] == 50.0
    assert 'overall_score' in result
    
    # 점수에 따른 등급 (100*0.4(40) + 0*0.3(0) + 50*0.3(15) = 55.0점)
    # Threshold가 B가 80점, C가 70점, D가 60점이라 F 등급 예상
    assert result['overall_score'] == 55.0
    assert result['grade'] == 'F'

def test_evaluate_student_not_found(evaluation_service, mock_db_session):
    """존재하지 않는 학생 ID 예외 검증"""
    query_mock = MagicMock()
    query_mock.filter.return_value.first.return_value = None
    mock_db_session.query.return_value = query_mock

    with pytest.raises(ValueError, match="학생 ID 999를 찾을 수 없습니다"):
        evaluation_service.evaluate_student(student_id=999, department_id=1)
