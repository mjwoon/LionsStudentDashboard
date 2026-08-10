# ADR 0001 — 공유 패키지 + uv workspace로 크로스패키지 중복 제거

- 상태: **Proposed (spike / 계획만)** — 실제 코드/배포 변경 없음
- 관련: 리팩토링 로드맵의 P4-C, PR #1(backend foundations)의 후속

## 1. 배경 (현재 상태)

`backend/`, `ai/`(Celery worker), `graphDB/`(빌드/분석 스크립트)가 각각 독립 파이썬 루트이며,
공유 코드를 **정식 패키지가 아니라 경로 조작**으로 끌어쓴다.

- `ai/tasks.py`: `sys.path.insert(0, BACKEND_PATH)` (`BACKEND_PATH=/backend`)로 backend 모듈 import.
- 배포: dev `docker-compose`와 prod `render.yaml` 모두 worker에 `PYTHONPATH=/app:/backend`를 주입하고,
  prod는 `ai/Dockerfile.prod`(context=repo 루트)가 backend를 이미지의 `/backend`에 복사한다.

### 중복 인벤토리 (근거)
1. **DB 세션 코드** — `ai/database.py` ≈ `backend/database.py`. 단 `ai`쪽엔 `get_db_session`(컨텍스트 매니저)이 있고 `backend`엔 없음 → 이미 드리프트.
2. **평가 캐시 writer** — `ai/tasks.py`가 `StudentRequirementStatus` 필드 매핑을 자체 재구현. backend엔 이제 `EvaluationCacheRepository.save_result`(SSOT)가 있음.
3. **입학연도 도출** — `ai/tasks.py`의 `int(str(student_id)[:4])`가 `EvaluationService.get_admission_year_from_student_id`와 중복.
4. **Neo4j 연결/설정** — `graphDB/*`가 자체 연결 + `load_dotenv`를 구현(backend `graph_service.Neo4jConnection`/`config.py`와 별개).
5. **도메인 재사용** — `ai`가 `models.models`, `services.evaluation_service`, `ai_services.ai_service`를 경로 조작으로 참조.

### 문제
- 경로 조작 패키징은 취약(IDE 분석 불가, import 순서 의존, 드리프트 유발 — §중복1이 실제 사례).
- 같은 로직이 여러 프로세스에 복제 → 버그 이중 수정(예: admission_year 버그가 backend/ai 각각 존재했음).

## 2. 결정

**uv workspace**를 도입하고, 공유 코드를 단일 패키지 `lions-core`로 수렴한다.
`backend`/`ai`/`graphDB`는 각각 `lions-core`를 의존하는 workspace 멤버가 된다.
(이미 uv 생태계이므로 자연스럽고, 도구가 버전/설치를 관리해 드리프트를 차단.)

## 3. 목표 구조

```
/ (workspace 루트)
  pyproject.toml            # [tool.uv.workspace] members = ["packages/*", "backend", "ai", "graphDB"]
  packages/
    lions-core/
      pyproject.toml
      lions_core/
        config.py           # 현재 backend/config.py
        db.py               # engine/session + get_db + get_db_session (통합 SSOT)
        models/             # 현재 backend/models/models.py
        constants.py        # grading(classify_grade) 포함
        domain/
          evaluation_service.py
          repositories/     # entities, evaluation_repository(save_result)
        graph.py            # Neo4jConnection (현재 graph_service 연결부)
  backend/  pyproject.toml(dep: lions-core)   # FastAPI, routers, schemas, upload/admin 서비스
  ai/       pyproject.toml(dep: lions-core)   # celery_app, tasks, ai_services
  graphDB/  pyproject.toml(dep: lions-core)   # 빌드타임 스크립트
```

원칙: **빌드타임(SBERT·유사도 생성, graphDB)** 과 **쿼리타임(backend graph_service)** 을 분리하되, Neo4j 연결/설정은 `lions_core.graph`로 공유.

## 4. 마이그레이션 단계 (각 단계 로컬 검증 가능, 배포 단계만 예외)

| # | 단계 | 검증 | 위험 |
|---|---|---|---|
| 1 | workspace 스켈레톤(루트 pyproject, `packages/lions-core`) + `config.py`·`db.py` 이관(`get_db`+`get_db_session` 통합). backend/ai import 갱신 | `uv sync`, import smoke, pytest | 중(import 처)|
| 2 | ORM 모델 → `lions_core.models`. `from models.models import` 일괄 갱신 | pytest | 중(대량 import) |
| 3 | 도메인(evaluation_service, repositories, constants/grading) → `lions_core.domain`. **ai/tasks가 `save_result` 재사용 → ai writer 제거**, admission_year 중복 제거 | pytest + ai import smoke | 중 |
| 4 | Neo4j 연결 → `lions_core.graph`. graphDB·backend가 재사용 | import smoke | 낮~중 |
| 5 | **배포 갱신** — Dockerfile(backend, ai/Dockerfile.prod), docker-compose(PYTHONPATH 훅 제거), render.yaml. `sys.path.insert` 제거 | ⚠️ **로컬 검증 불가 — staging 배포 필요** | **높음** |
| 6 | `ai/database.py` 삭제, 잔여 중복 정리, uv.lock 정리 | uv sync + pytest | 낮 |

전환 중에는 **재-export 심(shim)** 으로 구 import 경로를 살려 대량 변경을 흡수(예: 구 `database.py`가 `from lions_core.db import *`).

## 5. 영향 파일
- 신규: 루트 `pyproject.toml`, `packages/lions-core/**`.
- 대량 import 갱신: `backend/**`(`from database`, `from models.models`, `from services.evaluation_service`, `from constants`), `ai/tasks.py`, `ai/database.py`(삭제), `graphDB/**`.
- 배포: `backend/Dockerfile`, `ai/Dockerfile`, `ai/Dockerfile.prod`, `docker-compose.yml`, `render.yaml`.

## 6. 위험 · 완화 · 롤백
- **배포 파손(최고 위험, 로컬 검증 불가)** — Phase 5는 **staging/preview 배포로 먼저 검증**. 검증 전까지 기존 `PYTHONPATH=/app:/backend` 경로를 병행 유지(패키지 설치 + 경로 폴백)해 무중단 전환.
- **대량 import churn** — 단계별 재-export 심으로 흡수, 한 번에 한 계층만 이동.
- **순환 import** — 계층 규칙 유지(models ← repositories ← domain ← app). `lions_core` 내부에서 상위→하위 단방향.
- **`feature/benchmark` 충돌** — 벤치마크 계측이 `ai/tasks.py`를 수정 중. Phase 3에서 ai/tasks 변경 시 병합 충돌 1회 예상 → 두 브랜치 중 하나를 먼저 머지 후 rebase.
- **롤백** — 각 Phase = 독립 커밋/PR. Phase 5 이전은 순수 코드라 revert 용이. Phase 5는 배포 플래그로 게이트.

## 7. 검증 전략
- Phase 1~4·6: `uv sync` → `python -c import` smoke → `pytest`(현재 33개) 그린 유지.
- Phase 5: **로컬 불가.** 최소 `docker compose build && up`으로 컨테이너 기동 확인, 이후 render preview로 워커 태스크 1건 실행 검증.

## 8. 열린 질문 (착수 전 결정)
1. 패키지 이름: `lions-core` vs `lions_shared`.
2. `graphDB` 빌드 스크립트를 workspace 멤버로 넣을지, 연결부만 `lions_core.graph` 공유하고 스크립트는 독립 유지할지.
3. `AdminService` 파사드 유지 여부(별도 A 항목과 연동).
4. Phase 5 배포 전환 시 staging 환경 가용 여부.

## 9. 권장
Phase 1→4, 6은 **하나의 후속 PR**(순수 코드, 로컬 검증)로, **Phase 5(배포)는 staging 검증을 낀 별도 PR**로 분리한다. 이렇게 하면 "코드 수렴"의 이점을 먼저 안전하게 얻고, 되돌리기 어려운 배포 전환만 게이트할 수 있다.
