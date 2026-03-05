# 🏗️ Lions Student Dashboard - 전체 아키텍처

## 📐 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 (브라우저)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)                │
│                         Port: 5173                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ DashboardView│  │StudentDetail │  │  AdminView   │           │
│  │  (통계/차트)   │  │  (평가결과)     │  │ (데이터관리) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│          └─────────────────┬────api.ts──────────────┘           │
└─────────────────────────────┼───────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python)                     │
│                         Port: 8080                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API Routers (8개)                            │  │
│  │  students | courses | surveys | evaluation | admin |     │  │
│  │  admin_upload_grouped | dashboard | graph                │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Services (비즈니스 로직)                        │  │
│  │  EvaluationService | StudentService | AdminService |     │  │
│  │  GraphService (Neo4j)                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────┬─────────────────┬───────────────────┬──────────────┘
            │ SQL             │ Bolt (Cypher)      │ Celery Task
            ▼                 ▼                    ▼
┌───────────────────┐  ┌──────────────────┐  ┌────────────────────┐
│ PostgreSQL        │  │ Neo4j Graph DB   │  │  AI Worker (Celery) │
│ (pgvector)        │  │ Port: 7474, 7687 │  │  Port: -           │
│ Port: 5432        │  │ Course 노드 (854)│  │  bulk_evaluate     │
└───────────────────┘  └──────────────────┘  │  rebuild_graph     │
                                              └────────┬───────────┘
                                                       │ OpenAI API
                                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Redis (메시지 브로커/작업 큐)                   │
│                    Port: 6380 (host) / 6379 (container)         │
│             Celery 비동기 작업 큐 + 진행상황 상태 저장              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐳 Docker 컨테이너 구성

| 서비스 | 이미지 | 포트 | 설명 |
|--------|--------|------|------|
| **db** | pgvector/pgvector:pg16 | 5432 | PostgreSQL + 벡터 검색 |
| **redis** | redis:7-alpine | 6380:6379 | Celery 메시지 브로커 |
| **backend** | 커스텀 (FastAPI) | 8080 | Python REST API |
| **neo4j** | neo4j:latest | 7474, 7687 | 그래프 데이터베이스 |
| **neo4j-init** | 커스텀 (graphDB) | - | Neo4j 초기 그래프 데이터 로드 |
| **ai-worker** | 커스텀 (Celery) | - | 비동기 일괄 평가 + AI 총평 생성 |
| **frontend** | 커스텀 (React) | 5173 | Vite 개발 서버 |

**네트워크:**
- `default`: 기본 Docker 네트워크
- `course-graph-network`: Backend ↔ Neo4j 통신용

**볼륨:**
- `postgres_data`: PostgreSQL 데이터 영구 저장
- `neo4j_data`: Neo4j 그래프 데이터 영구 저장

---

## 🎯 주요 컴포넌트

### 1️⃣ Frontend (React + TypeScript)

**위치:** `frontend/src/`

```
frontend/src/
├── App.tsx                         # 메인 앱, 뷰 전환
├── api.ts                          # API 클라이언트 (백엔드 통신)
├── types.ts                        # TypeScript 타입 정의
├── constants.ts                    # 상수 정의
├── hooks/
│   └── useInactivityTimeout.ts     # 비활성 세션 타임아웃
└── components/
    ├── DashboardView.tsx           # 전체 통계 대시보드
    ├── AdminView.tsx               # 관리자 페이지
    ├── CurriculumView.tsx          # 커리큘럼 조회
    ├── DataUploadTab.tsx           # 데이터 업로드 UI
    ├── DiagnosisManagementTab.tsx  # 진단 관리 (배치 평가)
    ├── LoginView.tsx               # 로그인 화면
    ├── SessionWarningModal.tsx     # 세션 만료 경고 모달
    ├── SystemStatsTab.tsx          # 시스템 통계
    └── student/
        ├── StudentListView.tsx     # 학생 목록
        ├── StudentDetailView.tsx   # 학생 상세 정보 + 평가 결과
        ├── StudentCoursesTab.tsx   # 수강 이력 탭
        ├── StudentEntryTab.tsx     # 진입요건 탭
        ├── StudentSurveyTab.tsx    # 희망전공조사 탭
        ├── CurriculumTable.tsx     # 교육과정 테이블
        ├── DepartmentSelector.tsx  # 학과 선택기
        └── types.ts                # 학생 관련 타입
```

**기술 스택:**
- React 19 + TypeScript
- Tailwind CSS (스타일링)
- Vite (빌드 도구)
- Lucide React (아이콘)

---

### 2️⃣ Backend (FastAPI + Python)

**위치:** `backend/`

```
backend/
├── main.py                    # FastAPI 앱 진입점
├── database.py                # DB 연결 및 세션 관리
├── constants.py               # 상수 정의
├── seed_data.py               # 초기 데이터 시드
├── models/
│   ├── models.py              # SQLAlchemy 모델 (11개 테이블)
│   └── schemas.py             # Pydantic 스키마
├── routers/
│   ├── students.py            # 학생 API
│   ├── courses.py             # 과목/커리큘럼 API
│   ├── surveys.py             # 전공희망조사 API
│   ├── evaluation.py          # 평가 API ⭐
│   ├── admin.py               # 관리자 API
│   ├── admin_upload_grouped.py # 그룹별 통합 업로드 API (5그룹) ⭐
│   ├── dashboard.py           # 대시보드 통계 API
│   └── graph.py               # 그래프 분석 API (Neo4j) ⭐
└── services/
    ├── evaluation_service.py  # 평가 알고리즘 (3-메트릭)
    ├── student_service.py     # 학생 비즈니스 로직
    ├── admin_service.py       # 관리자 비즈니스 로직
    ├── seed_service.py        # 시드 데이터 서비스
    └── graph_service.py       # Neo4j 그래프 서비스 ⭐
```

---

### 3️⃣ AI Worker (Celery + OpenAI)

**위치:** `ai/`

```
ai/
├── celery_app.py              # Celery 앱 설정 (Redis 브로커)
├── database.py                # DB 세션 (Worker용)
├── tasks.py                   # Celery 태스크
│   ├── bulk_evaluate_task()   # 비동기 일괄 평가 (학생×학과)
│   └── rebuild_graph_task()   # GraphDB 비동기 재구축
└── ai_services/
    └── ai_service.py          # OpenAI API 총평 생성
        └── AIService
            ├── generate_evaluation_summary()  # 평가→자연어 총평
            └── _build_prompt()                # 프롬프트 구성
```

**AI 총평 흐름:**
```
평가 결과 → EVALUATION_PROMPT_TEMPLATE 구성
         → OpenAI API (gpt-4o-mini) 호출
         → "[상태값] : [진단 의견]" 형식 1줄 반환
         → analysis_json.ai_summary에 저장
```

**상태값:** 우수 | 양호 | 주의 | 위험

---

### 4️⃣ Graph DB (Neo4j)

**위치:** `graphDB/`

```
graphDB/
├── course_similarity_graph.py  # CourseGraphBuilder 클래스
│   ├── load_course_data()      # CSV 데이터 로드
│   ├── create_embeddings()     # Sentence-BERT 임베딩
│   ├── compute_similarity()    # 코사인 유사도 계산
│   └── create_graph()          # Neo4j 그래프 생성
│
├── course_graph_analysis.py    # CourseGraphAnalyzer 클래스
│   ├── get_degree_centrality() # 연결 중심성
│   ├── recommend_by_similarity() # 유사 과목 추천
│   ├── get_course_path()       # 경로 탐색
│   └── analyze_curriculum()    # 교과과정 분석
│
├── quick_start.py              # 빠른 시작 스크립트 (neo4j-init 컨테이너에서 실행)
├── final_course.csv            # 교과목 데이터 (854개)
└── pyproject.toml              # Python 의존성
```

**그래프 구조:**
```
(Course)─[:SIMILAR_TO {similarity: 0.85}]─>(Course)
    │
    └─[:IDENTICAL_ID {note: "동일 학수번호"}]─>(Course)

Course 노드 속성:
- id, code, name, department
- category, credits, description
```

---

## 📊 Database Schema

### PostgreSQL (11개 테이블)

```sql
┌─────────────────┐
│    colleges     │  # 단과대
├─────────────────┤
│ id, name        │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐       ┌──────────────────────────────┐
│  departments    │──────>│ department_entry_requirements │
├─────────────────┤       ├──────────────────────────────┤
│ id, code, name  │       │ 진입요건 (A/B/C 등급)         │
│ college_id      │       └──────────────────────────────┘
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐       ┌─────────────────────┐
│    students     │──────>│ course_enrollments  │
├─────────────────┤       ├─────────────────────┤
│ id, student_id  │       │ 수강 이력           │
│ name, gpa, ...  │       │ grade, semester     │
└─────────────────┘       └─────────────────────┘

┌───────────────────────────┐
│ student_requirement_status │ # 평가 결과 캐시 ⭐
├───────────────────────────┤
│ entry_requirement_score(40%)│
│ recommended_score (30%)   │
│ curriculum_score (30%)    │
│ overall_score, grade      │
│ analysis_json             │  ← ai_summary 포함
│ ai_summary                │  ← OpenAI 생성 총평
└───────────────────────────┘
```

### Neo4j (그래프)

```
노드: Course (854개)
관계: SIMILAR_TO (유사도 ≥ 0.8)
관계: IDENTICAL_ID (동일 학수번호, 다른 학과)
```

---

## 🔌 API 엔드포인트

### 학생 API (`/api/students`)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/students` | 학생 목록 (페이지네이션) |
| GET | `/students/{id}` | 학생 상세 |
| GET | `/students/{id}/courses` | 수강 이력 |

### 평가 API (`/api/evaluation`)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/student/{id}/department/{dept_id}` | 학과 적합도 평가 |
| GET | `/student/{id}/all-departments` | 전체 학과 평가 |
| POST | `/batch/department/{dept_id}` | 배치 평가 |

### 관리자 통합 업로드 API (`/api/admin/upload-grouped`) ⭐
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/org` | 단과대학 + 학과 통합 업로드 |
| POST | `/students` | 학생 + 희망전공조사 통합 업로드 |
| POST | `/requirements` | 진입요건 + 권장과목 통합 업로드 |
| POST | `/courses` | 과목 + 교육과정 통합 업로드 |
| POST | `/enrollments` | 수강 데이터 업로드 |

### 그래프 API (`/graph`) ⭐ Neo4j
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | Neo4j 연결 상태 |
| GET | `/statistics` | 그래프 통계 |
| GET | `/courses/search` | 교과목 검색 |
| GET | `/recommend/similar/{name}` | 유사 교과목 추천 |
| POST | `/recommend/multiple` | 복수 교과목 기반 추천 |
| GET | `/analysis/centrality` | 연결 중심성 분석 |
| GET | `/analysis/communities` | 클러스터 탐지 |
| GET | `/analysis/path` | 경로 탐색 |
| GET | `/curriculum` | 교과과정 구조 |
| GET | `/departments` | 학과 목록 |
| GET | `/categories` | 이수구분 목록 |

---

## 🔄 데이터 흐름

### **1. 학생 평가 흐름**
```
User → Frontend (학과 선택)
         ↓
       api.evaluation.getStudentEvaluation()
         ↓
       Backend: GET /api/evaluation/student/{id}/department/{dept_id}
         ↓
       EvaluationService (3개 메트릭 계산)
         ↓
       StudentRequirementStatus 캐시 조회/저장 (ai_summary 포함)
         ↓
       Frontend: Progress Bar + AI 총평 표시
```

### **2. 비동기 일괄 평가 흐름 (Celery)** ⭐
```
Admin → Frontend (배치 평가 요청)
         ↓
       Backend: POST /api/admin/bulk-evaluate
         ↓
       Celery Task (bulk_evaluate_task) → Redis Queue
         ↓
       AI Worker: 학생×학과 평가 순회
         ├─ EvaluationService.evaluate_student()
         └─ AIService.generate_evaluation_summary()  → OpenAI API
         ↓
       DB 저장 (ai_summary 포함)
         ↓
       Frontend: 진행률 폴링 (percent, current/total)
```

### **3. 교과목 추천 흐름 (Neo4j)**
```
User → Frontend (교과목 선택)
         ↓
       api.graph.getSimilarCourses()
         ↓
       Backend: GET /graph/recommend/similar/{course_name}
         ↓
       GraphService → Neo4j Cypher 쿼리
         ↓
       MATCH (c1:Course)-[r:SIMILAR_TO]-(c2:Course)
         ↓
       유사도 순 정렬 결과 반환
```

---

## 📈 평가 알고리즘 (3-메트릭 기반)

```python
# services/evaluation_service.py

종합 점수 =
    진입요건 충족 (40%)          # 진입요건 있으면 이수 비율, 없으면 100%
  + 권장과목 이수 (30%)          # Neo4j 유사과목 인정 비율 (similarity ≥ 0.7)
  + 교육과정 이수 (30%)          # 1학년 과목 Neo4j 유사과목 인정 비율

# 각 메트릭별 세부 지표
┌─────────────────────────────────────────────────────────────┐
│ 1️⃣ 진입요건 충족 (40%)                                      │
│    - 진입요건 있으면: 이수한 필수과목 / 전체 필수과목 × 100  │
│    - 진입요건 없으면: 100%                                   │
├─────────────────────────────────────────────────────────────┤
│ 2️⃣ 권장과목 이수 (30%)                                      │
│    - 동일과목 비율: [설강학과+학수코드] 정확히 일치          │
│    - 유사과목 비율: Neo4j SIMILAR_TO (similarity ≥ 0.7)     │
├─────────────────────────────────────────────────────────────┤
│ 3️⃣ 교육과정 이수 (30%)                                      │
│    - 동일과목 비율: 1학년 과목 [설강학과+학수코드] 일치      │
│    - 유사과목 비율: Neo4j SIMILAR_TO (similarity ≥ 0.7)     │
└─────────────────────────────────────────────────────────────┘

등급: A (≥90) | B (≥80) | C (≥70) | D (≥60) | F (<60)
AI 상태값: 우수 | 양호 | 주의 | 위험
```

---

## 🚀 실행 방법

### 전체 시스템 시작
```bash
# 1. 환경 변수 설정 (.env 파일)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
VITE_LOGIN_PASSWORD=...
VITE_ADMIN_PASSWORD=...

# 2. Docker 컨테이너 실행 (neo4j-init이 자동으로 그래프 데이터 로드)
docker-compose up -d --build

# 3. 데이터베이스 시드
docker exec fastapi_backend uv run python seed_data.py
```

### Neo4j 그래프 수동 재구축
```bash
# AI Worker를 통한 비동기 재구축 (권장)
# Admin UI → GraphDB 재구축 버튼

# 또는 직접 실행
cd graphDB
uv sync
uv run python quick_start.py
```

### 접속 URL
| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8080 |
| API Docs | http://localhost:8080/docs |
| Neo4j Browser | http://localhost:7474 |

---

## 🔐 환경 변수

```yaml
# Backend
DATABASE_URL: postgresql+psycopg://user:password@db:5432/my_db
REDIS_URL: redis://redis:6379/0
NEO4J_URI: bolt://neo4j-course-graph:7687
NEO4J_USER: neo4j
NEO4J_PASSWORD: password123
OPENAI_API_KEY: sk-...            # AI 총평 생성용
OPENAI_MODEL: gpt-4o-mini
CORS_ORIGINS: http://localhost:5173,https://your-domain.com

# AI Worker
DATABASE_URL: postgresql://user:password@db:5432/my_db
REDIS_URL: redis://redis:6379/0
OPENAI_API_KEY: sk-...
OPENAI_MODEL: gpt-4o-mini
BACKEND_PATH: /backend
PYTHONPATH: /app:/backend

# Frontend
VITE_API_URL: http://localhost:8080
VITE_LOGIN_PASSWORD: ...          # 일반 사용자 비밀번호
VITE_ADMIN_PASSWORD: ...          # 관리자 비밀번호
```

---

## 📊 데이터 규모

| 항목 | 수량 |
|------|------|
| 학생 | 303명 |
| 학과 | 40개 |
| 교과목 (PostgreSQL) | 수천 개 |
| 교과목 (Neo4j) | 854개 |
| 평가 결과 | 12,120개 (303 × 40) |
| 유사도 엣지 | 수천 개 (임계값 0.8 이상) |

---

이 아키텍처는 **학생 평가 시스템 + 교과목 추천 시스템 + AI 총평 생성**이 통합된 형태입니다! 🎉
