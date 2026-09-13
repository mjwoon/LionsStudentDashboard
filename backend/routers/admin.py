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
from services.upload_service import UploadService
from services.evaluation_admin_service import EvaluationAdminService
from typing import List, Optional
import json
import logging
import io
import math
import os
import ssl
import time

logger = logging.getLogger(__name__)

_celery_app_cache = None
_redis_client_cache = None


def _get_redis_url():
    """Redis URL을 가져오고 필요시 변환 (Upstash는 TLS 필수)"""
    import os
    url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    # https:// → rediss://
    if url.startswith("https://"):
        logger.warning("REDIS_URL이 https://로 시작합니다. rediss://로 변환합니다.")
        url = "rediss://" + url[len("https://"):]
    # Upstash는 TLS 필수: redis:// → rediss://
    if url.startswith("redis://") and "upstash" in url:
        logger.warning("Upstash URL이 redis://로 시작합니다. rediss://로 변환합니다.")
        url = "rediss://" + url[len("redis://"):]
    return url


# 큐에 넣은 작업을 우리 쪽에서도 적어 둔다.
#
# Celery 결과 키(celery-task-meta-*)는 워커가 실제로 집어야 생긴다. 그래서 그 키가
# 없다는 것만으로는 세 경우를 구분할 수 없었다 — 오타 난 job_id, 방금 큐에 들어간
# 작업, 워커가 죽어 영원히 안 돌 작업. 전부 PENDING으로 보였고 화면은 영원히 폴링했다.
# 큐잉 시점을 남겨두면 '없음 / 대기 / 지연'을 가를 수 있다.
JOB_REGISTRY_PREFIX = "lions:bulk-eval:job:"
JOB_REGISTRY_TTL_SECONDS = 60 * 60 * 24        # 하루면 진행 상황을 되찾기에 충분하다
# 이보다 오래 결과가 없으면 워커가 집지 않는 것으로 본다. 무료·유휴 상태의 워커가
# 깨어나는 시간을 감안해 넉넉하게 둔다.
JOB_STALE_AFTER_SECONDS = int(os.getenv("BULK_EVAL_STALE_AFTER_SECONDS", "300"))


PROGRESS_SNAPSHOT_PREFIX = "lions:bulk-eval:progress:"


def job_registry_key(job_id: str) -> str:
    return f"{JOB_REGISTRY_PREFIX}{job_id}"


def progress_snapshot_key(job_id: str) -> str:
    return f"{PROGRESS_SNAPSHOT_PREFIX}{job_id}"


def _stalled_seconds(r, job_id: str, progress: dict):
    """진행률이 멈춘 지 얼마나 됐는지. 아직 멈추지 않았으면 None.

    워커가 죽거나 진행률 기록이 끊기면 메타는 PROGRESS인 채로 굳는다. 화면은 그 차이를
    알 수 없어 영원히 폴링한다. 그래서 current가 마지막으로 '바뀐' 시각을 서버가 따로
    적어 두고, 그때부터 재는 것이 판정 근거다. 워커가 남긴 값만 보면 굳었다는 사실
    자체를 알 수 없다.
    """
    current = progress.get("current")
    if current is None:
        return None

    key = progress_snapshot_key(job_id)
    now = time.time()
    try:
        raw = r.get(key)
        if raw is not None:
            seen, ts = _decode(raw).rsplit(":", 1)
            if seen == str(current):
                waited = now - float(ts)
                # 움직이지 않았으면 기준점을 갱신하지 않는다 — 갱신하면 시계가 계속 초기화된다.
                return waited if waited > JOB_STALE_AFTER_SECONDS else None
        r.setex(key, JOB_REGISTRY_TTL_SECONDS, f"{current}:{now}")
    except Exception as e:
        logger.warning(f"진행률 스냅샷 처리 실패({job_id}): {e}")
    return None


def _decode(raw) -> str:
    return raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)


def _register_job(job_id: str) -> None:
    """큐잉 사실을 기록한다. 실패해도 큐잉 자체를 되돌리지는 않는다."""
    try:
        _get_redis_client().setex(
            job_registry_key(job_id), JOB_REGISTRY_TTL_SECONDS, str(time.time())
        )
    except Exception as e:
        logger.warning(f"job 대장 기록 실패({job_id}): {e}")


def _get_redis_client():
    """Redis 클라이언트 싱글톤 반환 (커넥션 풀 재사용)"""
    global _redis_client_cache
    if _redis_client_cache is None:
        import redis as redis_lib
        REDIS_URL = _get_redis_url()
        kwargs = {'socket_timeout': 10, 'socket_connect_timeout': 10}
        if REDIS_URL.startswith("rediss://"):
            kwargs['ssl_cert_reqs'] = 'none'
        _redis_client_cache = redis_lib.from_url(REDIS_URL, **kwargs)
    return _redis_client_cache


def _get_celery_app():
    """Celery 앱을 생성하는 헬퍼 (싱글톤, broker only)"""
    global _celery_app_cache
    if _celery_app_cache is not None:
        return _celery_app_cache

    from celery import Celery

    REDIS_URL = _get_redis_url()
    logger.info(f"Celery broker URL scheme: {REDIS_URL.split('://')[0]}")

    # broker만 설정, result backend는 사용하지 않음 (연결 문제 회피)
    celery_app = Celery("ai_worker", broker=REDIS_URL)

    # 연결 타임아웃 설정
    celery_app.conf.broker_transport_options = {
        'socket_timeout': 15,
        'socket_connect_timeout': 15,
        'retry_on_timeout': True,
        'max_retries': 5,
    }
    celery_app.conf.broker_connection_retry_on_startup = True

    if REDIS_URL.startswith("rediss://"):
        celery_app.conf.broker_use_ssl = {'ssl_cert_reqs': ssl.CERT_NONE}

    _celery_app_cache = celery_app
    return celery_app

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
        return UploadService.upload_colleges(db, colleges_data)
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
        return UploadService.upload_advisors(db, advisors_data)
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
        return UploadService.upload_departments(db, departments_data)
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
        return UploadService.upload_courses(db, courses_data)
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
        return UploadService.upload_major_surveys(db, surveys_data)
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
    return UploadService.upload_students(db, students_data)


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
        return UploadService.upload_students(db, students_data)
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
    return UploadService.upload_enrollments(db, enrollments_data)


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
        return UploadService.upload_enrollments(db, enrollments_data)
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
        return UploadService.upload_curriculums(db, curriculums_data)
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
        return UploadService.upload_recommendations(db, recs_data)
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
        return UploadService.upload_requirements(db, reqs_data)
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
        return UploadService.upload_requirement_courses(db, req_courses_data)
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
        celery_app = _get_celery_app()
        
        task = celery_app.send_task(
            "bulk_evaluate",
            kwargs={
                "force_recalculate": request.force_recalculate,
                "student_ids": request.student_ids,
                "department_ids": request.department_ids
            }
        )
        
        _register_job(task.id)

        return {
            "job_id": task.id,
            "status": "QUEUED",
            "message": "일괄 평가가 큐에 등록되었습니다. job_id로 진행상황을 확인하세요."
        }
    
    except ImportError:
        # Celery 미설치 시 기존 동기 방식 폴백
        logger.warning("Celery 미설치 - 동기 방식으로 실행")
        return EvaluationAdminService.bulk_evaluate(db, request)
    except Exception as e:
        logger.error(f"태스크 큐잉 실패: {e}")
        raise HTTPException(status_code=500, detail=f"태스크 큐잉 실패: {str(e)}")


@router.get("/evaluate/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    비동기 일괄 평가 진행 상태 조회 (Redis에서 직접 조회)
    """
    try:
        r = _get_redis_client()

        # Celery는 결과를 'celery-task-meta-{task_id}' 키에 저장
        raw = r.get(f"celery-task-meta-{job_id}")
        if raw is None:
            queued_at = r.get(job_registry_key(job_id))
            if queued_at is None:
                # 큐에 넣은 적이 없다. 화면이 폴링을 멈출 수 있어야 한다.
                return {
                    "job_id": job_id,
                    "status": "NOT_FOUND",
                    "error": "해당 작업을 찾을 수 없습니다. 이미 만료됐거나 실행된 적이 없습니다.",
                }

            try:
                waited = time.time() - float(_decode(queued_at))
            except (TypeError, ValueError):
                waited = 0.0

            if waited > JOB_STALE_AFTER_SECONDS:
                return {
                    "job_id": job_id,
                    "status": "STALE",
                    "error": (
                        f"큐에 들어간 지 {int(waited // 60)}분이 지나도록 처리가 시작되지 않았습니다. "
                        "AI 워커가 실행 중인지 확인하세요."
                    ),
                }

            return {
                "job_id": job_id,
                "status": "PENDING",
                "progress": {
                    "current": 0,
                    "total": 0,
                    "percent": 0,
                    "status": "대기 중..."
                }
            }

        import json as _json
        data = _json.loads(raw)
        status = data.get("status", "UNKNOWN")

        response = {
            "job_id": job_id,
            "status": status,
        }

        if status == "PROGRESS":
            progress = data.get("result", {}) or {}
            stalled = _stalled_seconds(r, job_id, progress)
            if stalled is not None:
                return {
                    "job_id": job_id,
                    "status": "STALE",
                    "error": (
                        f"{int(stalled // 60)}분째 진행이 없습니다 "
                        f"({progress.get('current')}/{progress.get('total')}에서 멈춤). "
                        "AI 워커 로그를 확인하세요."
                    ),
                    # 어디서 멈췄는지 보여줘야 다시 돌릴지 판단할 수 있다.
                    "progress": progress,
                }
            response["progress"] = progress
        elif status == "SUCCESS":
            response["result"] = data.get("result")
        elif status == "FAILURE":
            response["error"] = str(data.get("result", "Unknown error"))

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


@router.get("/redis-test")
async def test_redis_connection():
    """Redis 연결 테스트 (디버깅용)"""
    try:
        r = _get_redis_client()
        pong = r.ping()
        return {
            "status": "connected",
            "ping": pong,
            "url_scheme": _get_redis_url().split("://")[0],
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "url_scheme": _get_redis_url().split("://")[0],
        }


@router.post("/rebuild-graph")
async def trigger_rebuild_graph():
    """
    GraphDB 재구축 비동기 실행 (Celery Worker)
    """
    try:
        celery_app = _get_celery_app()
        
        task = celery_app.send_task("rebuild_graph")
        
        _register_job(task.id)

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
    return EvaluationAdminService.get_cached_evaluation_stats(db)


@router.delete("/evaluate/cache")
async def clear_cached_evaluations(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """캐시된 진단 결과 삭제"""
    return EvaluationAdminService.clear_cached_evaluations(db, department_id)


@router.delete("/data/all")
async def delete_all_data(db: Session = Depends(get_db)):
    """모든 업로드 데이터 삭제"""
    return AdminService.delete_all_data(db)


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
