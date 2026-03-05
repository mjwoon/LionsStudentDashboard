# Lions Student Dashboard

한양대학교 LIONS 학생 관리 대시보드 - 학생, 학과, 강좌 및 설문조사 관리 시스템

## 📋 프로젝트 개요

이 프로젝트는 학생 정보, 학과 정보, 강좌 정보, 그리고 전공 설문조사를 관리하는 풀스택 웹 애플리케이션입니다. Neo4j 그래프 데이터베이스를 활용한 교과목 유사도 분석 및 추천 기능, Celery 기반 비동기 일괄 평가, OpenAI를 활용한 AI 총평 생성 기능이 포함되어 있습니다.

### 기술 스택

**Backend:**
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (pgvector)
- Neo4j (그래프 DB - 교과목 유사도 분석)
- Celery (비동기 작업 처리)
- uv (패키지 관리자)
- Pydantic (데이터 검증)

**AI:**
- OpenAI API (gpt-4o-mini, AI 총평 생성)
- Celery Worker (비동기 일괄 평가)

**Frontend:**
- React 19.2.0
- TypeScript
- Vite
- Tailwind CSS

**Infrastructure:**
- Docker & Docker Compose
- Redis (Celery 메시지 브로커)

## 🚀 시작하기

### 필수 요구사항

- Docker Desktop
- Git
- OpenAI API Key (AI 총평 기능 사용 시)

### 1. 프로젝트 클론

```bash
git clone https://github.com/mjwoon/LionsStudentDashboard.git
cd LionsStudentDashboard
```

### 2. 환경 변수 설정

```bash
# 프로젝트 루트에 .env 파일 생성
OPENAI_API_KEY=sk-...           # AI 총평 생성 (없으면 총평 미생성)
OPENAI_MODEL=gpt-4o-mini
VITE_LOGIN_PASSWORD=...         # 일반 사용자 로그인 비밀번호
VITE_ADMIN_PASSWORD=...         # 관리자 로그인 비밀번호
```

### 3. 프로젝트 빌드 및 실행

```bash
# 전체 프로젝트 빌드 및 실행 (neo4j-init이 자동으로 그래프 데이터 로드)
docker-compose up -d --build
```

### 4. 초기 데이터 설정

1. 프론트엔드 로그인 후 **관리자 페이지**로 이동
2. `Data Upload` 탭에서 학생, 과목, 학과 요건, 수강 이력을 CSV 형태로 일괄 업로드
3. 데이터가 업로드되면 자동으로 DB에 적재되고 평가 시스템이 활성화됩니다.

### 5. 접속

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Frontend** | http://localhost:5173 | React 웹 애플리케이션 |
| **Backend API** | http://localhost:8080 | FastAPI REST API |
| **API 문서** | http://localhost:8080/docs | Swagger UI |
| **Neo4j Browser** | http://localhost:7474 | 그래프 DB 관리 콘솔 |
| **PostgreSQL** | localhost:5432 | 관계형 DB |
| **Redis** | localhost:6380 | Celery 메시지 브로커 |

## 📁 프로젝트 구조

```
LionsStudentDashboard/
├── backend/                    # FastAPI 백엔드
│   ├── models/                # 데이터베이스 모델 및 스키마
│   │   ├── models.py          # SQLAlchemy ORM 모델
│   │   └── schemas.py         # Pydantic 스키마
│   ├── routers/               # API 라우터
│   │   ├── students.py        # 학생 관리 API
│   │   ├── courses.py         # 강좌/학과 관리 API
│   │   ├── surveys.py         # 설문조사 API
│   │   ├── evaluation.py      # 학생 평가 API
│   │   ├── dashboard.py       # 대시보드 통계 API
│   │   ├── admin.py           # 관리자 API
│   │   ├── admin_upload_grouped.py  # 그룹별 통합 업로드 API
│   │   └── graph.py           # 그래프 분석 API (Neo4j)
│   ├── services/              # 비즈니스 로직
│   │   ├── evaluation_service.py  # 평가 알고리즘 (3-메트릭)
│   │   ├── student_service.py     # 학생 서비스
│   │   ├── admin_service.py       # 관리자 서비스
│   │   └── graph_service.py       # Neo4j 그래프 서비스
│   ├── main.py                # FastAPI 앱 진입점
│   ├── database.py            # DB 연결 설정
│   └── Dockerfile
│
├── ai/                         # AI Worker (Celery)
│   ├── ai_services/
│   │   └── ai_service.py      # OpenAI 기반 AI 총평 생성
│   ├── celery_app.py          # Celery 앱 설정
│   ├── database.py            # Worker용 DB 연결
│   ├── tasks.py               # 비동기 태스크 (일괄 평가, 그래프 재구축)
│   └── Dockerfile
│
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   ├── student/               # 학생 관련 컴포넌트
│   │   │   │   ├── StudentListView.tsx
│   │   │   │   ├── StudentDetailView.tsx
│   │   │   │   ├── StudentCoursesTab.tsx
│   │   │   │   ├── StudentEntryTab.tsx
│   │   │   │   └── StudentSurveyTab.tsx
│   │   │   ├── DashboardView.tsx      # 대시보드
│   │   │   ├── AdminView.tsx          # 관리자
│   │   │   ├── CurriculumView.tsx     # 커리큘럼
│   │   │   ├── LoginView.tsx          # 로그인
│   │   │   └── SessionWarningModal.tsx
│   │   ├── hooks/
│   │   │   └── useInactivityTimeout.ts
│   │   ├── App.tsx            # 메인 앱
│   │   ├── api.ts             # API 클라이언트
│   │   └── types.ts           # TypeScript 타입
│   └── Dockerfile.dev
│
├── graphDB/                    # Neo4j 그래프 DB 모듈
│   ├── course_similarity_graph.py  # 그래프 빌더
│   ├── course_graph_analysis.py    # 그래프 분석
│   ├── quick_start.py              # 빠른 시작 스크립트
│   ├── final_course.csv            # 교과목 데이터 (854개)
│   └── README.md
│
├── docker-compose.yml          # Docker 구성
├── ARCHITECTURE.md             # 아키텍처 문서
└── README.md                   # 프로젝트 문서
```

## 🛠️ 개발 가이드

### Docker 컨테이너 관리

```bash
# 컨테이너 중지
docker-compose down

# 특정 서비스 재시작
docker-compose restart backend

# 로그 확인
docker-compose logs -f backend
docker-compose logs -f ai-worker
docker-compose logs -f neo4j

# 컨테이너 상태 확인
docker-compose ps

# 볼륨 포함 완전 초기화
docker-compose down -v
```

### 로컬 개발 (Docker 없이)

각 서비스를 개별적으로 실행할 수 있습니다. 로컬 개발 시 PostgreSQL, Redis, Neo4j는 Docker로 실행하는 것을 권장합니다.

```bash
# 인프라 서비스만 Docker로 실행
docker-compose up -d db redis neo4j
```

---

#### Backend (FastAPI)

```bash
cd backend

# 의존성 설치 (uv 패키지 관리자 사용)
uv sync

# 개발 서버 실행 (hot reload 지원)
uv run fastapi dev main.py --host 0.0.0.0 --port 8080

# 또는 프로덕션 모드
uv run fastapi run main.py --host 0.0.0.0 --port 8080
```

- API 문서: http://localhost:8080/docs (Swagger UI)
- 환경 변수: 프로젝트 루트의 `.env` 파일에서 설정

---

#### Frontend (React + Vite)

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행 (hot reload 지원)
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 미리보기
npm run preview

# 린트 검사
npm run lint
```

- 개발 서버: http://localhost:5173
- API 호출은 `src/api.ts`를 통해 중앙 관리

---

#### AI Worker (Celery)

```bash
cd ai

# 의존성 설치
uv sync

# Celery 워커 실행
BACKEND_PATH=../backend PYTHONPATH=..:../backend uv run celery -A tasks worker --loglevel=info
```

- Redis 브로커 필요 (localhost:6380)
- 비동기 작업: 학생 일괄 평가 (`bulk_evaluate`), 그래프 재구축 (`rebuild_graph`)
- 백엔드 모듈 직접 import (`BACKEND_PATH` 환경변수 설정 필요)

---

#### GraphDB (Neo4j 그래프 생성)

```bash
cd graphDB

# 의존성 설치
uv sync

# 교과목 유사도 그래프 생성
uv run python quick_start.py

# 또는 개별 스크립트 실행
uv run python course_similarity_graph.py  # 그래프 빌드
uv run python course_graph_analysis.py    # 그래프 분석
```

- Neo4j 필요 (localhost:7474, 기본 계정: neo4j/password123)
- Sentence-BERT 임베딩으로 교과목 유사도 계산
- 유사도 ≥ 0.8인 교과목 간 `SIMILAR_TO` 관계 생성
- Docker 실행 시 `neo4j-init` 컨테이너가 자동으로 처리

## 📊 주요 API 엔드포인트

### 학생 API (`/api/students`)
- `GET /students` - 학생 목록 (페이지네이션, 검색)
- `GET /students/{id}` - 학생 상세 정보

### 평가 API (`/api/evaluation`)
- `GET /student/{id}/department/{dept_id}` - 학생 학과 적합도 평가
- `GET /student/{id}/all-departments` - 전체 학과 평가

### 관리자 통합 업로드 API (`/api/admin/upload-grouped`)
- `POST /org` - 단과대학 + 학과 통합 업로드
- `POST /students` - 학생 + 희망전공조사 통합 업로드
- `POST /requirements` - 진입요건 + 권장과목 통합 업로드
- `POST /courses` - 과목 + 교육과정 통합 업로드
- `POST /enrollments` - 수강 데이터 업로드

### 그래프 API (`/graph`) - Neo4j
- `GET /graph/health` - Neo4j 연결 상태
- `GET /graph/statistics` - 그래프 통계
- `GET /graph/courses/search` - 교과목 검색
- `GET /graph/recommend/similar/{course_name}` - 유사 교과목 추천
- `POST /graph/recommend/multiple` - 복수 교과목 기반 추천
- `GET /graph/analysis/centrality` - 연결 중심성 분석
- `GET /graph/curriculum` - 교과과정 구조 분석

## 🐛 트러블슈팅

### 포트 충돌
```yaml
# docker-compose.yml에서 포트 변경
backend:
  ports:
    - "8081:8080"  # 왼쪽 숫자 변경
```

### Neo4j 연결 실패
```bash
# Neo4j 컨테이너 상태 확인
docker logs neo4j-course-graph

# Neo4j 재시작
docker-compose restart neo4j
```

### AI Worker 연결 실패
```bash
# AI Worker 로그 확인
docker logs ai_worker

# Redis 연결 확인
docker-compose logs redis
```

### 데이터베이스 완전 초기화
```bash
docker-compose down -v
docker-compose up --build
```

## 📝 API 문서

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 👥 개발자

- GitHub: [@mjwoon](https://github.com/mjwoon)

## 📄 라이선스

This project is licensed under the MIT License.
