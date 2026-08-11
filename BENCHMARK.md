# BENCHMARK.md — 대량 평가 파이프라인 처리 시간 실측

> 규칙: **실제 실행 출력만** 기록. 추정치는 "외삽" 표기 + 산출식 명시.
> 측정일: 2026-07-28. 계측: `time.perf_counter()`. 원자료: `ai/tasks.py`(계측 코드), `ai/_bench_runner.py`(러너).

---

## 0. 측정 전 버그 수정 (완료)

`backend/services/admin_service.py`의 동기 대량평가 경로에서 입학년도 계산이 항상 폴백되던 버그를 수정함.

```python
# 수정 전 (admin_service.py):
#   admission_year = int(student.student_id[:4])
#   → student_id는 Integer라 슬라이스 시 TypeError → except → 항상 2025
# 수정 후 (admin_service.py:696):
    admission_year = int(str(student.student_id)[:4])
```

**이 시드에서 수정의 실제 효과(실측 확인)**: 시드된 학번은 9자리(`2024xxxxx`, `2025xxxxx`). 분포 = **2024학번 118명 + 2025학번 116명**.
- 수정 전: 전원 `TypeError → admission_year=2025`.
- 수정 후: 2024학번은 `2024`, 2025학번은 `2025`로 정확히 계산.

러너는 학번 오름차순으로 학생을 선택하므로 **소·중규모 동기 측정(앞 10·50명)은 전부 2024학번** → 수정 전 2025(오답) 대신 **2024(정답) 진입요건으로 평가**됨. 따라서 아래 동기 측정값은 **수정본 기준**이며, 수정 전과 진입요건 조회 경로가 달라진다.

---

## 1. 실행 환경 (실측)

| 항목 | 값 |
|---|---|
| 호스트 | Apple M2, 8 core, 16 GB, macOS (Darwin 25.5.0, arm64) |
| Docker | 28.1.1 / Compose v2.35.1-desktop.1 |
| DB | `pgvector/pgvector:pg16` (`fullstack_db`) |
| Redis | `redis:7-alpine` |
| Neo4j | `neo4j:latest` (로컬 컨테이너, Aura 아님) |
| Backend | `fastapi dev` (uvicorn), `backend/database.py` **echo=True** |
| Worker | Celery `--concurrency=2`, `ai/database.py` echo=False |
| LLM | OpenAI `gpt-4o-mini` (실제 키 사용) |

### 시드된 실제 데이터 (루트 CSV를 `/api/admin/upload-grouped/*`로 적재 — `seed_data.py`는 HEAD에서 삭제되어 없음)
| 대상 | 실제 건수 |
|---|---|
| 학생 | **234** (2024학번 118 + 2025학번 116) |
| 학과 | **39** (id 100–802, id>100 은 38개) |
| 과목 (PostgreSQL) | 318 |
| 수강이력 | 3,757 |
| 진입요건 그룹 | 50 |
| Neo4j 노드 / SIMILAR_TO 엣지 | 1,493 / 3,866 (평균 유사도 0.5454) |
| 평가 캐시 행(측정 후) | 9,126 (`student_requirement_status`) |

- ⚠️ 문서상 규모(`ARCHITECTURE.md`: 303×40=12,120)와 다름. **실제 전체 = 234×39 = 9,126.** 12,120은 미시드 → §5에서 per-eval 실측으로 외삽만.

---

## 2. 측정 방법

- `ai/tasks.py` `bulk_evaluate_task`에 구간별 `perf_counter` 누적기 추가(학생/학과 조회 / `evaluate_student`(Neo4j 포함) / `generate_evaluation_summary`(OpenAI) / `db.commit()`), 태스크 종료 시 1회 출력.
- 러너 `ai/_bench_runner.py` — **각 조건 = 별도 프로세스**(Neo4j `lru_cache` 콜드, 공정). 입력은 학번 오름차순 앞 N명 / 앞 M학과, `force_recalculate=True`(캐시 우회).
- 3조건: **비동기(real)** `bulk_evaluate_task.apply()` eager in-process(OpenAI 실호출) / **비동기(스텁)** `generate_evaluation_summary`를 고정 문자열 몽키패치 / **동기** `AdminService.bulk_evaluate`(동일 입력, **AI 총평 생성 없음** — 코드상 부재).
- 전 조건 `neo4j_available=true`, `error_count=0` 확인.

---

## 3. 결과 — 조건 × 규모별 총 소요 시간 (실측)

| 규모 | 건수 | 동기 (AI 없음) | 비동기 (스텁, AI 없음) | 비동기 (real LLM) |
|---|---|---|---|---|
| 소 10×5 | 50 | **5.271 s** | **4.808 s** | **69.814 s** |
| 중 50×10 | 500 | **46.063 s** | **44.658 s** | **649.551 s** (10.8분) |
| 전체 234×39 | 9,126 | **788.811 s** (13.1분) | **748.132 s** (12.5분) | 미측정 (real LLM 9,126콜 = 비용/시간 과다) |

1건당 평균(per_eval, 실측):
| 규모 | 동기 | 비동기 스텁 | 비동기 real |
|---|---|---|---|
| 50 | 105.42 ms | 95.55 ms | 1395.83 ms |
| 500 | 92.13 ms | 89.27 ms | 1299.05 ms |
| 9,126 | 86.44 ms | 81.98 ms | — |

> **핵심**: 동기(AI 없음) ≈ 비동기 스텁(AI 없음). 둘 다 `evaluate_student`(Neo4j+계산)가 지배. 비동기 real은 여기에 OpenAI가 얹혀 **약 14–15배** 증가.

---

## 4. 구간별 시간 분해 (비동기 태스크 계측, 실측)

| 규모 | 조건 | 조회 query_s | 평가 eval_s (Neo4j+계산) | LLM ai_s (OpenAI) | 커밋 commit_s | total_s |
|---|---|---|---|---|---|---|
| 50 | 스텁 | 0.0022 | 4.708 | 0.00003 | 0.031 | 4.778 |
| 50 | real | 0.0020 | 5.973 | **63.562** | 0.083 | 69.792 |
| 500 | 스텁 | 0.0025 | 44.211 | 0.0003 | 0.182 | 44.635 |
| 500 | real | 0.0026 | 55.304 | **591.873** | 0.626 | 649.527 |
| 9,126 | 스텁 | 0.0047 | 742.244 | 0.005 | 1.870 | 748.108 |

파생 지표(실측 기반 계산):
- **OpenAI가 전체에서 차지하는 비중**: 50건 real 63.562/69.792 = **91.1%**, 500건 real 591.873/649.527 = **91.1%**.
- **OpenAI 1콜 평균**: 50건 63.562/50 = **1.271 s**, 500건 591.873/500 = **1.184 s**.
- **evaluate_student(Neo4j+계산) 1건 평균**: 스텁 500 = 88.4 ms, 스텁 9,126 = 81.3 ms, real 500 = 110.6 ms.
- **db.commit()(학생 단위) 1회 평균**: 500 스텁 0.182/50 = 3.6 ms, 9,126 스텁 1.870/234 = 8.0 ms.
- **학생/학과 조회**: 2–5 ms 상수(규모 무관).

> 임베딩은 **런타임 계산 없음**(그래프 빌드 시 사전계산). `eval_s`는 Neo4j `SIMILAR_TO` 조회 + 파이썬 점수 계산이며 SBERT 인코딩은 발생하지 않음.

---

## 5. 1건당 평균 → 12,120건 외삽

문서상 규모 12,120(303×40)은 미시드라 **직접 측정 불가**. 아래는 실측 per-eval로부터의 **외삽(추정)**:

| 조건 | 사용한 실측 per-eval | 12,120건 외삽 |
|---|---|---|
| 비동기 real LLM | 1299.05 ms (500건) | 12,120 × 1.29905 s = **15,744 s ≈ 262분 ≈ 4.37시간** |
| 비동기 real LLM (소규모 기준) | 1395.83 ms (50건) | 12,120 × 1.39583 s = **16,917 s ≈ 4.70시간** |
| 비동기 스텁(AI 없음) | 81.98 ms (9,126건) | 12,120 × 0.08198 s = **994 s ≈ 16.6분** |
| 동기(AI 없음) | 86.44 ms (9,126건) | 12,120 × 0.08644 s = **1,048 s ≈ 17.5분** |

참고 — **실측된 전체 규모(9,126)**: 동기 789 s(13.1분), 비동기 스텁 748 s(12.5분). real LLM은 9,126×~1.2 s ≈ 3.3시간으로 추정(미측정).

> 결론: 12,120건을 실제 파이프라인(AI 총평 포함)으로 돌리면 **약 4.4–4.7시간** 규모. AI 총평을 빼면 **약 17분**. 시간의 91%가 OpenAI 호출.

---

## 6. HTTP 타임아웃 검증 (4단계, 실측)

**선결 사실**: 대량 평가를 **동기로 실행하는 HTTP 엔드포인트는 설계상 없음.** `POST /api/admin/evaluate/bulk`은 Celery 큐잉 전용이고 동기 폴백(`admin_service.bulk_evaluate`)은 Celery `ImportError` 시에만 진입(`backend/routers/admin.py:429-432`). → 검증을 위해 backend에 **임시 동기 라우트**(`POST /api/_bench/sync-bulk`) 추가·측정 후 제거함.

500건(50×10) 동기 HTTP 요청 실측:

| 테스트 | 조건 | 결과 |
|---|---|---|
| A | 클라이언트 `curl --max-time 10` | **10.003 s에서 절단** (curl exit 28, `http_code=000`) |
| B | 클라이언트 타임아웃 없음 | **98.974 s 완주** (`http_code=200`, success_count=500) |

해석(실측 근거):
- **uvicorn(`fastapi dev`)은 요청 타임아웃을 설정하지 않음** → 서버 자체는 99 s 요청을 끝까지 처리(테스트 B). **절단 주체는 서버가 아니라 클라이언트/프록시**(테스트 A).
- 로컬엔 리버스 프록시가 없어 **프로덕션(Render) 프록시 절단은 로컬 미재현**. 단 측정된 동기 소요(500건 = 99 s, 9,126건 = 789 s)는 통상적인 프록시/LB 한계(수십 초~100 s대)를 **초과** → 비동기 큐잉 설계의 실측 근거.
- ⚠️ HTTP 경로 98.974 s는 §3의 worker in-process 46.063 s(동일 500건 동기)의 약 **2.1배**. 원인 = backend 엔진 **`echo=True`**(`backend/database.py:12`, SQL 전문 로깅). worker(`ai/database.py`, echo=False)와 직접 비교 시 이 차이를 감안. → 프로덕션에서 `echo=True`는 그 자체로 지연·로그량을 배가시키는 문제.

---

## 7. 재현 방법 / 측정에 사용한 변경점

- **0단계 버그 수정**(유지): `backend/services/admin_service.py:696` `int(str(student.student_id)[:4])`.
- **유지된 계측 코드**: `ai/tasks.py` `bulk_evaluate_task` 내 `perf_counter` 구간 누적 + 종료 시 `[BENCHMARK] ...` 로그/`timing` 반환.
- **러너**: `ai/_bench_runner.py` (모드 `async`/`sync`/`async_stub`, 인자 `n_students n_depts`).
- **시드**: 루트 CSV를 `POST /api/admin/upload-grouped/{org,students,courses,curriculum,requirements,enrollments}` 순으로 업로드.
- **worker 임시 의존성**: 동기 경로가 backend `models.schemas`(pydantic[email]) import → worker 이미지에 `email-validator` 미포함이라 컨테이너에 임시 설치 후 `uv run --no-sync` 실행. (worker는 원래 동기 경로를 쓰지 않으므로 프로덕션 무영향)
- **임시 라우트**: §6의 `/api/_bench/sync-bulk`는 측정 후 `backend/main.py`에서 제거함.

---

## 8. 측정으로 드러난 사실 요약

1. 대량 평가 시간의 **~91%가 OpenAI 총평 호출**(1콜 ≈ 1.2 s, 직렬). 나머지는 Neo4j 유사도+계산(≈81–110 ms/건), 커밋·조회는 무시할 수준.
2. **동기 vs 비동기(스텁)는 처리 시간이 사실상 동일** — 비동기의 이점은 "빠른 처리"가 아니라 **HTTP 요청에서 장시간 작업을 분리**하는 것.
3. `--concurrency=2`여도 단일 대량요청은 태스크 1개라 **병렬화되지 않음**(직렬). 실측 500건 real = 650 s가 그 증거.
4. 동기 HTTP 500건 = 99 s로 완주 가능하나 클라이언트/프록시 타임아웃에 취약(10 s 컷 재현) → **비동기 큐잉 설계의 정량적 근거**.
5. backend `echo=True`가 동일 작업을 약 2배 느리게 만듦(46 s→99 s) — 운영 설정 개선 포인트.
6. 0단계 버그 수정으로 동기 경로가 이제 정확한 입학년도(이 시드에선 2024/2025)로 평가 — 수정 전엔 전원 2025로 폴백돼 측정이 무의미했음.
