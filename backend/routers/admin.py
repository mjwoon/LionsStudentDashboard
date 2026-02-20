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


@router.post("/evaluate/bulk")
async def bulk_evaluate(
    request: BulkEvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    대량 진단을 비동기로 실행 (Celery Worker)
    
    - 즉시 job_id를 반환하고 백그라운드에서 처리
    - GET /evaluate/jobs/{job_id}로 진행상황 확인
    """
    try:
        from celery import Celery
        import os
        
        REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
        celery_app = Celery("ai_worker", broker=REDIS_URL, backend=REDIS_URL)
        
        task = celery_app.send_task(
            "bulk_evaluate",
            kwargs={
                "force_recalculate": request.force_recalculate,
                "student_ids": request.student_ids,
                "department_ids": request.department_ids
            }
        )
        
        return {
            "job_id": task.id,
            "status": "QUEUED",
            "message": "일괄 평가가 큐에 등록되었습니다. job_id로 진행상황을 확인하세요."
        }
    
    except ImportError:
        # Celery 미설치 시 기존 동기 방식 폴백
        logger.warning("Celery 미설치 - 동기 방식으로 실행")
        return AdminService.bulk_evaluate(db, request)
    except Exception as e:
        logger.error(f"태스크 큐잉 실패: {e}")
        raise HTTPException(status_code=500, detail=f"태스크 큐잉 실패: {str(e)}")


@router.get("/evaluate/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    비동기 일괄 평가 진행 상태 조회
    
    Returns:
        - status: PENDING | STARTED | PROGRESS | SUCCESS | FAILURE
        - progress: 진행률 정보 (PROGRESS 상태일 때)
        - result: 최종 결과 (SUCCESS 상태일 때)
    """
    try:
        from celery.result import AsyncResult
        from celery import Celery
        import os
        
        REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
        celery_app = Celery("ai_worker", broker=REDIS_URL, backend=REDIS_URL)
        
        result = AsyncResult(job_id, app=celery_app)
        
        response = {
            "job_id": job_id,
            "status": result.state,
        }
        
        if result.state == "PROGRESS":
            response["progress"] = result.info
        elif result.state == "SUCCESS":
            response["result"] = result.result
        elif result.state == "FAILURE":
            response["error"] = str(result.info)
        elif result.state == "PENDING":
            response["progress"] = {
                "current": 0,
                "total": 0,
                "percent": 0,
                "status": "대기 중..."
            }
        
        return response
    
    except ImportError:
        raise HTTPException(status_code=501, detail="Celery가 설치되지 않았습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


@router.get("/evaluate/stats", response_model=CachedEvaluationStats)
async def get_cached_evaluation_stats(db: Session = Depends(get_db)):
    """캐시된 진단 결과 통계 조회"""
    return AdminService.get_cached_evaluation_stats(db)


@router.delete("/evaluate/cache")
async def clear_cached_evaluations(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """캐시된 진단 결과 삭제"""
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
            "GET /api/admin/evaluate/jobs/{job_id}",
            "GET /api/admin/evaluate/stats",
            "DELETE /api/admin/evaluate/cache"
        ]
    }
