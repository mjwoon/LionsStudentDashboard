# 🚀 시작하기 및 설치 가이드 (Installation Guide)

이 문서는 Lions Student Dashboard 프로젝트의 로컬 환경 구성, Docker 빌드 및 개발 가이드를 설명합니다.

## 필수 요구사항

- Docker Desktop
- Git
- OpenAI API Key (AI 총평 기능 사용 시)

## 1. 프로젝트 클론

```bash
git clone https://github.com/mjwoon/LionsStudentDashboard.git
cd LionsStudentDashboard
```

## 2. 환경 변수 설정

```bash
# 프로젝트 루트에 .env 파일 생성
OPENAI_API_KEY=sk-...           # AI 총평 생성 (없으면 총평 미생성)
OPENAI_MODEL=gpt-4o-mini
VITE_LOGIN_PASSWORD=...         # 일반 사용자 로그인 비밀번호
VITE_ADMIN_PASSWORD=...         # 관리자 로그인 비밀번호
```

## 3. 프로젝트 빌드 및 실행

```bash
# 전체 프로젝트 빌드 및 실행 (neo4j-init이 자동으로 그래프 데이터 로드)
docker-compose up -d --build
```

## 4. 초기 데이터 설정

1. 프론트엔드 로그인 후 **관리자 페이지**로 이동
2. `Data Upload` 탭에서 학생, 과목, 학과 요건, 수강 이력을 CSV 형태로 일괄 업로드
3. 데이터가 업로드되면 자동으로 DB에 적재되고 평가 시스템이 활성화됩니다.

## 5. 서비스 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Frontend** | http://localhost:5173 | React 웹 애플리케이션 |
| **Backend API** | http://localhost:8080 | FastAPI REST API |
| **API 문서** | http://localhost:8080/docs | Swagger UI |
| **Neo4j Browser** | http://localhost:7474 | 그래프 DB 관리 콘솔 |
| **PostgreSQL** | localhost:5432 | 관계형 DB |
| **Redis** | localhost:6380 | Celery 메시지 브로커 |

---

# 📁 개발자용 가이드 (Developer Guide)

## Docker 컨테이너 관리

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

## 로컬 개발 (Docker 없이)

각 서비스를 개별적으로 실행할 수 있습니다. 로컬 개발 시 PostgreSQL, Redis, Neo4j는 Docker로 실행하는 것을 권장합니다.

```bash
# 인프라 서비스만 Docker로 실행
docker-compose up -d db redis neo4j
```

### Backend (FastAPI)

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

### Frontend (React + Vite)

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

### AI Worker (Celery)

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

### GraphDB (Neo4j 그래프 생성)

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

---

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
