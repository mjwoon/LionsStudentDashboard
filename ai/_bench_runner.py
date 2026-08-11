"""
[임시] 대량 평가 파이프라인 벤치마크 러너.
ai-worker 컨테이너에서 실행. 매 호출 = 새 프로세스(=콜드 lru_cache).

사용법:
  uv run python /app/_bench_runner.py <mode> <n_students> <n_depts>
  mode: async | sync | async_stub
출력: 마지막 줄에 'BENCHRESULT ' + JSON

주: 워크스페이스 이관(ADR 0001) 이후 공유 코드는 lions_core 에서 import 한다.
sync 모드는 backend 모듈(EvaluationAdminService)이 경로상 접근 가능할 때만 동작한다.
"""
import sys, time, json, logging
logging.disable(logging.WARNING)

mode = sys.argv[1]
n_students = int(sys.argv[2])
n_depts = int(sys.argv[3])

from lions_core.db import get_db_session
from lions_core.models import Student, Department

# 결정적 입력 선택: id 오름차순으로 앞에서 N개
with get_db_session() as db:
    student_ids = [s.student_id for s in
                   db.query(Student).order_by(Student.student_id).limit(n_students).all()]
    department_ids = [d.id for d in
                      db.query(Department).order_by(Department.id).limit(n_depts).all()]

total = len(student_ids) * len(department_ids)

try:
    from lions_core.graph_connection import is_graph_available
    _graph = is_graph_available()
except Exception as e:
    _graph = f"err:{e!r}"

result = {
    "mode": mode,
    "n_students": len(student_ids),
    "n_depts": len(department_ids),
    "total_evaluations": total,
    "neo4j_available": _graph,
}

if mode in ("async", "async_stub"):
    import ai_services.ai_service as ai_mod
    if mode == "async_stub":
        # 3단계: OpenAI 호출을 즉시 고정 문자열 반환 스텁으로 교체
        ai_mod.AIService.generate_evaluation_summary = \
            lambda self, r: "[STUB] 양호 : 벤치마크용 고정 문자열"

    import celery_app as ca
    ca.celery_app.conf.task_always_eager = True
    ca.celery_app.conf.task_store_eager_result = False
    ca.celery_app.conf.result_backend = "cache+memory://"

    import tasks as tasks_mod
    t0 = time.perf_counter()
    res = tasks_mod.bulk_evaluate_task.apply(kwargs={
        "force_recalculate": True,
        "student_ids": student_ids,
        "department_ids": department_ids,
    })
    wall = time.perf_counter() - t0
    payload = res.result
    result["wall_s"] = round(wall, 3)
    result["success_count"] = payload.get("success_count")
    result["error_count"] = payload.get("error_count")
    result["timing"] = payload.get("timing")

elif mode == "sync":
    # 동기 폴백 경로: AI 총평 생성 없음. (AdminService 파사드 제거 → EvaluationAdminService)
    from services.evaluation_admin_service import EvaluationAdminService
    from models.schemas import BulkEvaluationRequest
    req = BulkEvaluationRequest(
        force_recalculate=True,
        student_ids=student_ids,
        department_ids=department_ids,
    )
    with get_db_session() as db:
        t0 = time.perf_counter()
        resp = EvaluationAdminService.bulk_evaluate(db, req)
        wall = time.perf_counter() - t0
    result["wall_s"] = round(wall, 3)
    result["success_count"] = resp.success_count
    result["error_count"] = resp.error_count
    result["per_eval_ms"] = round(wall / total * 1000, 2) if total else 0.0
    result["note"] = "sync path: no AI summary (evaluation_admin_service.bulk_evaluate)"

else:
    result["error"] = f"unknown mode {mode}"

print("BENCHRESULT " + json.dumps(result, ensure_ascii=False), flush=True)
