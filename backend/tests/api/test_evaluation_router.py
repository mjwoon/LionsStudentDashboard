from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from database import get_db

client = TestClient(app)

def test_get_student_evaluation_success():
    """학생 평가 API 조회 성공 통합 테스트 (모킹 사용)"""
    
    student_id = 20260001
    department_id = 99
    
    # DB 의존성 오버라이딩
    mock_db = MagicMock()
    mock_student = MagicMock()
    mock_student.student_id = student_id
    mock_student.overall_score = None  # 캐시 로직을 우회하기 위함
    
    # db.query(Student).filter(...).first() 체이닝 모킹 설정
    mock_db.query.return_value.filter.return_value.first.return_value = mock_student
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    # EvaluationService 오버라이딩 (패치가 아닌 의존성을 주입받는 내부 객체 모킹)
    with patch("routers.evaluation.EvaluationService") as mock_eval_service_class:
        mock_eval_service_instance = MagicMock()
        mock_eval_service_class.return_value = mock_eval_service_instance
        
        mock_result = {
            "student_id": student_id,
            "department_name": "산업경영공학과",
            "evaluated_at": "2026-03-08T12:00:00Z",
            "entry_requirement_score": 100.0,
            "recommended_exact_rate": 80.0,
            "recommended_similar_rate": 20.0,
            "curriculum_exact_rate": 90.0,
            "curriculum_similar_rate": 10.0,
            "overall_score": 95.5,
            "grade": "A",
            "ai_summary": "현재 상태는 [우수]합니다.",
            "detailed_results": []
        }
        
        mock_eval_service_instance.evaluate_student.return_value = mock_result
        mock_eval_service_instance.get_curriculum_details.return_value = {}
        
        response = client.get(f"/api/evaluation/student/{student_id}/department/{department_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == student_id
        assert data["overall_score"] == 95.5
        assert data["grade"] == "A"
        
    app.dependency_overrides.clear()
    
def test_get_student_evaluation_not_found():
    """학생 정보가 없을 때 HTTP 404 예외 검증"""
    
    # DB 조회 시 None 반환 시뮬레이션
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    response = client.get(f"/api/evaluation/student/999/department/1")
    
    assert response.status_code == 404
    assert "학번 999를 찾을 수 없습니다" in response.json()["detail"]
    
    app.dependency_overrides.clear()
