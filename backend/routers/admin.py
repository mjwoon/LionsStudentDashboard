"""
관리자용 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import (
    CourseDataUpload, StudentDataUpload, EnrollmentDataUpload, MajorSurveyDataUpload,
    CurriculumDataUpload, RecommendationDataUpload, RequirementDataUpload,
    CollegeDataUpload, DepartmentDataUpload, RequirementCourseDataUpload,
    AdvisorDataUpload,
    DataUploadResponse, BulkEvaluationRequest, BulkEvaluationResponse,
    CachedEvaluationStats
)
from services.admin_service import AdminService
from typing import List, Optional
import json
import logging
import io
import math

logger = logging.getLogger(__name__)

async def parse_upload_file(file: UploadFile) -> List[dict]:
    """
    Parse JSON, CSV, or Excel file into a list of dictionaries.
    Uses pandas for CSV and Excel.
    """
    filename = file.filename.lower()
    contents = await file.read()
    
    if filename.endswith(".json"):
        data = json.loads(contents)
    elif filename.endswith(".csv") or filename.endswith(".xlsx") or filename.endswith(".xls"):
        import pandas as pd
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # student_id 열이 있으면 정수로 변환 (공백이나 \.0 등 제거 후)
        if "student_id" in df.columns:
            df["student_id"] = pd.to_numeric(df["student_id"], errors='coerce').astype('Int64')
            
        # Replace NaN with None so pydantic models can handle missing values (optional fields)
        df = df.where(pd.notnull(df), None)
        data = df.to_dict(orient="records")
        # pandas의 where가 NaN을 완전히 제거하지 못하는 경우 보완
        for row in data:
            for key, val in row.items():
                if isinstance(val, float) and math.isnan(val):
                    row[key] = None
    else:
        raise ValueError("Unsupported file format. Please upload .json, .csv, or .xlsx files.")
    
    # JSON에서도 student_id가 str로 들어오는 경우 int로 변환
    for row in data:
        if "student_id" in row and isinstance(row["student_id"], str) and row["student_id"].isdigit():
            row["student_id"] = int(row["student_id"])
    
    return data

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)


@router.post("/upload/colleges/file", response_model=DataUploadResponse)
async def upload_colleges_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """파일로 대학 데이터 일괄 업로드"""
    try:
        data = await parse_upload_file(file)
        colleges_data = [CollegeDataUpload(**item) for item in data]
        return AdminService.upload_colleges(db, colleges_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/advisors/file", response_model=DataUploadResponse)
async def upload_advisors_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """파일로 지도교수 데이터 일괄 업로드"""
    try:
        data = await parse_upload_file(file)
        advisors_data = [AdvisorDataUpload(**item) for item in data]
        return AdminService.upload_advisors(db, advisors_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/departments/file", response_model=DataUploadResponse)
async def upload_departments_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """파일로 학과 데이터 일괄 업로드"""
    try:
        data = await parse_upload_file(file)
        departments_data = [DepartmentDataUpload(**item) for item in data]
        return AdminService.upload_departments(db, departments_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/courses/file", response_model=DataUploadResponse)
async def upload_courses_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """CSV/JSON 파일로 과목 데이터 일괄 업로드 (한국어 헤더 지원)"""
    try:
        data = await parse_upload_file(file)
        courses_data = [CourseDataUpload(**item) for item in data]
        return AdminService.upload_courses(db, courses_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/upload/major-surveys/file", response_model=DataUploadResponse)
async def upload_major_surveys_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    JSON/CSV 파일로 희망전공 조사(major_surveys) 데이터 일괄 업로드
    """
    try:
        data = await parse_upload_file(file)
        surveys_data = [MajorSurveyDataUpload(**item) for item in data]
        return AdminService.upload_major_surveys(db, surveys_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
            "department_id": 100,
            "advisor_id": 1,
            "pride": "L",
            "class_number": 1,
            "track": "자연계열"
        },
        ...
    ]
    """
    try:
        data = await parse_upload_file(file)
        students_data = [StudentDataUpload(**item) for item in data]
        return AdminService.upload_students(db, students_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
        data = await parse_upload_file(file)
        enrollments_data = [EnrollmentDataUpload(**item) for item in data]
        return AdminService.upload_enrollments(db, enrollments_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/curriculums/file", response_model=DataUploadResponse)
async def upload_curriculums_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        data = await parse_upload_file(file)
        curriculums_data = [CurriculumDataUpload(**item) for item in data]
        return AdminService.upload_curriculums(db, curriculums_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/recommendations/file", response_model=DataUploadResponse)
async def upload_recommendations_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        data = await parse_upload_file(file)
        recs_data = [RecommendationDataUpload(**item) for item in data]
        return AdminService.upload_recommendations(db, recs_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload/requirements/file", response_model=DataUploadResponse)
async def upload_requirements_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        data = await parse_upload_file(file)
        reqs_data = [RequirementDataUpload(**item) for item in data]
        return AdminService.upload_requirements(db, reqs_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/upload/requirement-courses/file", response_model=DataUploadResponse)
async def upload_requirement_courses_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        data = await parse_upload_file(file)
        req_courses_data = [RequirementCourseDataUpload(**item) for item in data]
        return AdminService.upload_requirement_courses(db, req_courses_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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


@router.post("/rebuild-graph")
async def trigger_rebuild_graph():
    """
    GraphDB 재구축 비동기 실행 (Celery Worker)
    """
    try:
        from celery import Celery
        import os
        
        REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
        celery_app = Celery("ai_worker", broker=REDIS_URL, backend=REDIS_URL)
        
        task = celery_app.send_task("rebuild_graph")
        
        return {
            "job_id": task.id,
            "status": "QUEUED",
            "message": "GraphDB 재구축이 큐에 등록되었습니다."
        }
    except Exception as e:
        logger.error(f"태스크 큐잉 실패: {e}")
        raise HTTPException(status_code=500, detail=f"태스크 큐잉 실패: {str(e)}")


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
            "POST /api/admin/upload/major-surveys/file",
            "POST /api/admin/upload/students",
            "POST /api/admin/upload/students/file",
            "POST /api/admin/upload/enrollments",
            "POST /api/admin/upload/enrollments/file",
            "POST /api/admin/upload/curriculums/file",
            "POST /api/admin/upload/recommendations/file",
            "POST /api/admin/upload/requirements/file",
            "POST /api/admin/evaluate/bulk",
            "POST /api/admin/rebuild-graph",
            "GET /api/admin/evaluate/jobs/{job_id}",
            "GET /api/admin/evaluate/stats",
            "DELETE /api/admin/evaluate/cache"
        ]
    }
