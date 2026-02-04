# Lions Student Dashboard

한양대학교 LIONS 학생 관리 대시보드 - 학생, 학과, 강좌 및 설문조사 관리 시스템

## 📋 프로젝트 개요

이 프로젝트는 학생 정보, 학과 정보, 강좌 정보, 그리고 전공 설문조사를 관리하는 풀스택 웹 애플리케이션입니다. Neo4j 그래프 데이터베이스를 활용한 교과목 유사도 분석 및 추천 기능도 포함되어 있습니다.

### 기술 스택

**Backend:**
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (pgvector)
- Neo4j (그래프 DB - 교과목 유사도 분석)
- uv (패키지 관리자)
- Pydantic (데이터 검증)

**Frontend:**
- React 19.2.0
- TypeScript
- Vite
- Tailwind CSS

**Infrastructure:**
- Docker & Docker Compose
- Redis

## 🚀 시작하기

### 필수 요구사항

- Docker Desktop
- Git

### 1. 프로젝트 클론

```bash
git clone https://github.com/mjwoon/LionsStudentDashboard.git
cd LionsStudentDashboard
```

### 2. 프로젝트 빌드 및 실행

**전체 프로젝트 빌드 및 실행:**

```bash
docker-compose up --build
```

**백그라운드 실행:**

```bash
docker-compose up -d --build
```

### 3. 초기 데이터 설정

```bash
# 데이터베이스 시드 데이터 삽입
docker exec fastapi_backend uv run python seed_data.py

# 배치 평가 실행 (학생별 학과 적합도 계산)
docker exec fastapi_backend uv run python batch_evaluate_all.py
```

### 4. Neo4j 그래프 데이터 로드 (선택사항)

```bash
# graphDB 폴더에서 Neo4j에 교과목 유사도 그래프 생성
cd graphDB
uv run python quick_start.py
```

### 5. 접속

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Frontend** | http://localhost:5173 | React 웹 애플리케이션 |
| **Backend API** | http://localhost:8080 | FastAPI REST API |
| **API 문서** | http://localhost:8080/docs | Swagger UI |
| **Neo4j Browser** | http://localhost:7474 | 그래프 DB 관리 콘솔 |
| **PostgreSQL** | localhost:5432 | 관계형 DB |
| **Redis** | localhost:6379 | 캐시/메시지 브로커 |

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
│   │   └── graph.py           # 그래프 분석 API (Neo4j)
│   ├── services/              # 비즈니스 로직
│   │   ├── evaluation_service.py  # 평가 알고리즘
│   │   ├── student_service.py     # 학생 서비스
│   │   ├── admin_service.py       # 관리자 서비스
│   │   └── graph_service.py       # Neo4j 그래프 서비스
│   ├── data/                  # 커리큘럼 JSON 데이터
│   ├── main.py                # FastAPI 앱 진입점
│   ├── database.py            # DB 연결 설정
│   └── Dockerfile
│
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── components/        # React 컴포넌트
│   │   │   ├── DashboardView.tsx      # 대시보드
│   │   │   ├── StudentDetailView.tsx  # 학생 상세
│   │   │   ├── CurriculumView.tsx     # 커리큘럼
│   │   │   └── AdminView.tsx          # 관리자
│   │   ├── App.tsx            # 메인 앱
│   │   ├── api.ts             # API 클라이언트
│   │   └── types.ts           # TypeScript 타입
│   └── Dockerfile
│
├── graphDB/                    # Neo4j 그래프 DB 모듈
│   ├── course_similarity_graph.py  # 그래프 빌더
│   ├── course_graph_analysis.py    # 그래프 분석
│   ├── quick_start.py              # 빠른 시작 스크립트
│   ├── final_course.csv            # 교과목 데이터
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
docker-compose logs -f neo4j

# 컨테이너 상태 확인
docker-compose ps

# 볼륨 포함 완전 초기화
docker-compose down -v
```

### 로컬 개발 (Docker 없이)

**백엔드:**
```bash
cd backend
uv sync
uv run fastapi dev main.py --host 0.0.0.0 --port 8080
```

**프론트엔드:**
```bash
cd frontend
npm install
npm run dev
```

## 📊 주요 API 엔드포인트

### 학생 API (`/api/students`)
- `GET /students` - 학생 목록 (페이지네이션, 검색)
- `GET /students/{id}` - 학생 상세 정보

### 평가 API (`/api/evaluation`)
- `GET /student/{id}/department/{dept_id}` - 학생 학과 적합도 평가
- `GET /student/{id}/all-departments` - 전체 학과 평가

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
