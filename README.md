# Lions Student Dashboard

한양대학교 LIONS 학생 관리 대시보드 - 학생, 학과, 강좌 및 설문조사 관리 시스템

## 📋 프로젝트 개요

이 프로젝트는 학생 정보, 학과 정보, 강좌 정보, 그리고 전공 설문조사를 관리하는 풀스택 웹 애플리케이션입니다.

### 기술 스택

**Backend:**
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (pgvector)
- uv (패키지 관리자)
- Pydantic (데이터 검증)

**Frontend:**
- React 19.2.0
- TypeScript
- Vite
- CSS

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

### 2. 환경 설정

Docker Compose를 사용하므로 별도의 환경 설정이 필요하지 않습니다. 모든 종속성은 컨테이너 내에서 관리됩니다.

### 3. 프로젝트 빌드 및 실행

**전체 프로젝트 빌드 및 실행:**

```bash
docker-compose up --build
```

**백그라운드 실행:**

```bash
docker-compose up -d --build
```

**특정 서비스만 빌드:**

```bash
# 백엔드만 빌드
docker-compose build backend

# 프론트엔드만 빌드
docker-compose build frontend
```

### 4. 접속

프로젝트가 실행되면 다음 주소로 접속할 수 있습니다:

- **Frontend (React)**: http://localhost:5173
- **Backend API**: http://localhost:8080
- **API 문서 (Swagger)**: http://localhost:8080/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📁 프로젝트 구조

```
LionsStudentDashboard/
├── backend/                 # FastAPI 백엔드
│   ├── models/             # 데이터베이스 모델 및 스키마
│   │   ├── database.py     # SQLAlchemy ORM 모델
│   │   └── schemas.py      # Pydantic 스키마
│   ├── routers/            # API 라우터
│   │   ├── students.py     # 학생 관리 API
│   │   ├── courses.py      # 강좌/학과 관리 API
│   │   └── surveys.py      # 설문조사 API
│   ├── main.py             # FastAPI 애플리케이션 엔트리포인트
│   ├── database.py         # 데이터베이스 연결 설정
│   ├── seed_data.py        # 샘플 데이터 생성 스크립트
│   ├── pyproject.toml      # Python 의존성 (uv)
│   └── Dockerfile          # 백엔드 Docker 이미지
│
├── frontend/               # React 프론트엔드
│   ├── src/
│   │   ├── App.tsx         # 메인 애플리케이션 컴포넌트
│   │   ├── api.ts          # API 클라이언트 유틸리티
│   │   ├── App.css         # 스타일시트
│   │   └── main.tsx        # React 엔트리포인트
│   ├── package.json        # npm 의존성
│   ├── vite.config.ts      # Vite 설정
│   └── Dockerfile          # 프론트엔드 Docker 이미지
│
└── docker-compose.yml      # Docker Compose 설정
```

## 🛠️ 개발 가이드

### Backend 개발

**로컬에서 백엔드 실행 (Docker 없이):**

```bash
cd backend

# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync

# 데이터베이스 초기화 및 샘플 데이터 생성
uv run python seed_data.py

# 개발 서버 실행
uv run fastapi dev main.py --host 0.0.0.0 --port 8080
```

**주요 API 엔드포인트:**

- `GET /api/students` - 학생 목록 조회 (페이지네이션, 필터링)
- `GET /api/students/{student_id}` - 학생 상세 정보
- `POST /api/students` - 새 학생 등록
- `GET /api/departments` - 학과 목록
- `GET /api/departments/{dept_id}/curriculum` - 학과 커리큘럼
- `GET /api/surveys/summary` - 설문조사 통계
- `POST /api/surveys/submit` - 설문 제출

### Frontend 개발

**로컬에서 프론트엔드 실행 (Docker 없이):**

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

**빌드:**

```bash
npm run build
```

### Docker 컨테이너 관리

**컨테이너 중지:**

```bash
docker-compose down
```

**컨테이너 재시작:**

```bash
docker-compose restart
```

**특정 서비스 재시작:**

```bash
docker-compose restart backend
docker-compose restart frontend
```

**로그 확인:**

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend
docker-compose logs -f frontend
```

**컨테이너 상태 확인:**

```bash
docker-compose ps
```

## 📊 데이터베이스

### 데이터 모델

- **College**: 단과대학 정보
- **Department**: 학과 정보
- **Advisor**: 지도교수 정보
- **Student**: 학생 정보
- **Course**: 강좌 정보
- **CourseEnrollment**: 수강 신청 정보
- **SurveyRound**: 설문조사 회차
- **MajorSurvey**: 전공 설문 응답

### 샘플 데이터

초기 실행 시 자동으로 생성되는 샘플 데이터:
- 4개 단과대학
- 5개 학과
- 3명의 지도교수
- 50명의 학생
- 7개 강좌
- 수강신청 데이터
- 2개의 설문조사 회차 및 응답

## 🐛 트러블슈팅

### 포트 충돌

이미 사용 중인 포트가 있다면 `docker-compose.yml` 파일에서 포트를 변경하세요:

```yaml
services:
  backend:
    ports:
      - "8080:8080"  # 왼쪽 숫자를 변경 (예: "8081:8080")
  
  frontend:
    ports:
      - "5173:5173"  # 왼쪽 숫자를 변경
```

### Docker 볼륨 초기화

데이터베이스를 완전히 초기화하려면:

```bash
docker-compose down -v
docker-compose up --build
```

### 백엔드가 시작되지 않는 경우

로그를 확인하세요:

```bash
docker-compose logs backend
```

데이터베이스 연결 문제일 수 있으니 PostgreSQL 컨테이너가 정상 실행 중인지 확인:

```bash
docker-compose ps
```

## 📝 API 문서

API의 상세한 문서는 서버 실행 후 다음 주소에서 확인할 수 있습니다:

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## 🤝 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

This project is licensed under the MIT License.

## 👥 개발자

- GitHub: [@mjwoon](https://github.com/mjwoon)

## 📧 문의

프로젝트에 대한 문의사항은 Issues 탭을 이용해주세요.
