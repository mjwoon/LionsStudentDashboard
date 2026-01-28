"""
관리자용 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import (
    CourseDataUpload, StudentDataUpload, EnrollmentDataUpload,
    DataUploadResponse, BulkEvaluationRequest, BulkEvaluationResponse,
    CachedEvaluationStats
)
from services.admin_service import AdminService
from typing import List, Optional
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)


@router.post("/upload/courses", response_model=DataUploadResponse)
async def upload_courses(
    courses_data: List[CourseDataUpload],
    db: Session = Depends(get_db)
):
    """
    과목 데이터 일괄 업로드/업데이트
    
    - 기존 과목 코드가 있으면 업데이트
    - 없으면 새로 생성
    """
    return AdminService.upload_courses(db, courses_data)


@router.post("/upload/courses/file", response_model=DataUploadResponse)
async def upload_courses_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    JSON 파일로 과목 데이터 일괄 업로드
    
    파일 형식:
    [
        {
            "course_code": "CSE101",
            "course_name": "컴퓨터공학개론",
            "credits": 3,
            "course_type": "전공필수",
            "department_code": "CSE",
            "course_year": 1,
            "semester": 1
        },
        ...
    ]
    """
    try:
        contents = await file.read()
        data = json.loads(contents)
        courses_data = [CourseDataUpload(**item) for item in data]
        return AdminService.upload_courses(db, courses_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/students", response_model=DataUploadResponse)
async def upload_students(
    students_data: List[StudentDataUpload],
    db: Session = Depends(get_db)
):
    """
    학생 데이터 일괄 업로드/업데이트
    
    - 기존 학번이 있으면 업데이트
    - 없으면 새로 생성
    """
    return AdminService.upload_students(db, students_data)


@router.post("/upload/students/file", response_model=DataUploadResponse)
async def upload_students_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    JSON 파일로 학생 데이터 일괄 업로드
    
    파일 형식:
    [
        {
            "student_id": "2024123456",
            "name": "홍길동",
            "email": "hong@hanyang.ac.kr",
            "phone": "010-1234-5678",
            "department_code": "CSE",
            "pride": "L",
            "class_number": 1,
            "track": "자연계열"
        },
        ...
    ]
    """
    try:
        contents = await file.read()
        data = json.loads(contents)
        students_data = [StudentDataUpload(**item) for item in data]
        return AdminService.upload_students(db, students_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/enrollments", response_model=DataUploadResponse)
async def upload_enrollments(
    enrollments_data: List[EnrollmentDataUpload],
    db: Session = Depends(get_db)
):
    """
    수강 데이터 일괄 업로드/업데이트
    
    - 동일한 학생-과목-학년-학기 조합이 있으면 업데이트
    - 없으면 새로 생성
    """
    return AdminService.upload_enrollments(db, enrollments_data)


@router.post("/upload/enrollments/file", response_model=DataUploadResponse)
async def upload_enrollments_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    JSON 파일로 수강 데이터 일괄 업로드
    
    파일 형식:
    [
        {
            "student_id": "2024123456",
            "course_code": "CSE101",
            "year": 2024,
            "semester": 1,
            "completion_type": "전공필수",
            "is_retake": false,
            "grade": "A+",
            "numeric_grade": 4.5
        },
        ...
    ]
    """
    try:
        contents = await file.read()
        data = json.loads(contents)
        enrollments_data = [EnrollmentDataUpload(**item) for item in data]
        return AdminService.upload_enrollments(db, enrollments_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/evaluate/bulk", response_model=BulkEvaluationResponse)
async def bulk_evaluate(
    request: BulkEvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    대량 진단 실행 및 결과 캐싱
    
    - student_ids: 특정 학생들만 진단 (없으면 전체)
    - department_ids: 특정 학과들만 진단 (없으면 전체)
    - force_recalculate: True이면 기존 결과 무시하고 재계산
    
    이 엔드포인트는 시간이 오래 걸릴 수 있으므로
    백그라운드 작업으로 실행하는 것을 권장합니다.
    """
    return AdminService.bulk_evaluate(db, request)


@router.get("/evaluate/stats", response_model=CachedEvaluationStats)
async def get_cached_evaluation_stats(db: Session = Depends(get_db)):
    """
    캐시된 진단 결과 통계 조회
    
    - 전체 캐시 수
    - 학과별 캐시 수
    - 마지막 업데이트 시간
    """
    return AdminService.get_cached_evaluation_stats(db)


@router.delete("/evaluate/cache")
async def clear_cached_evaluations(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    캐시된 진단 결과 삭제
    
    - department_id: 특정 학과의 캐시만 삭제 (없으면 전체)
    """
    return AdminService.clear_cached_evaluations(db, department_id)


@router.get("/health")
async def admin_health():
    """관리자 API 상태 확인"""
    return {
        "status": "healthy",
        "module": "admin",
        "endpoints": [
            "POST /api/admin/upload/courses",
            "POST /api/admin/upload/courses/file",
            "POST /api/admin/upload/students",
            "POST /api/admin/upload/students/file",
            "POST /api/admin/upload/enrollments",
            "POST /api/admin/upload/enrollments/file",
            "POST /api/admin/evaluate/bulk",
            "GET /api/admin/evaluate/stats",
            "DELETE /api/admin/evaluate/cache"
        ]
    }
