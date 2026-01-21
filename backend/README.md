# Lions Student Dashboard - Backend API

한양대학교 LIONS 학생 관리 대시보드 백엔드 API 서버입니다.

## 기술 스택

- **FastAPI**: 고성능 Python 웹 프레임워크
- **SQLAlchemy**: ORM (Object-Relational Mapping)
- **Pydantic**: 데이터 검증 및 직렬화
- **uv**: 빠른 Python 패키지 관리자
- **SQLite**: 개발용 데이터베이스 (프로덕션에서는 PostgreSQL 권장)

## 프로젝트 구조

```
backend/
├── main.py                 # FastAPI 애플리케이션 진입점
├── database.py             # 데이터베이스 연결 및 설정
├── seed_data.py           # 샘플 데이터 생성 스크립트
├── models/
│   ├── database.py        # SQLAlchemy 모델 정의
│   └── schemas.py         # Pydantic 스키마 정의
├── routers/
│   ├── students.py        # 학생 관리 API 엔드포인트
│   ├── courses.py         # 과목 및 교육과정 API 엔드포인트
│   └── surveys.py         # 전공 희망 조사 API 엔드포인트
├── pyproject.toml         # 프로젝트 의존성 정의
└── uv.lock                # uv 의존성 잠금 파일
```

## 설치 및 실행

### 1. 의존성 설치

```bash
cd backend
uv sync
```

### 2. 샘플 데이터 생성

```bash
rm c:/Users/82106/Workspace/LionsStudentDashboard/backend/lions_dashboard.db 
uv run python seed_data.py
```

### 3. 서버 실행

```bash
uv run fastapi dev main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 4. API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### 학생 관리

- `GET /api/students` - 학생 목록 조회 (필터링, 페이징 지원)
- `GET /api/students/{student_id}` - 특정 학생 상세 정보
- `GET /api/students/{student_id}/courses` - 학생 수강 이력
- `GET /api/students/{student_id}/surveys` - 학생 전공 희망 조사 이력
- `POST /api/students` - 신규 학생 등록

### 과목 및 교육과정

- `GET /api/courses` - 전체 과목 목록 (유형별 필터)
- `GET /api/courses/entry-requirements` - 전공 진입 필수 과목
- `GET /api/departments` - 학과 리스트
- `GET /api/departments/{id}/courses` - 학과별 과목 조회
- `GET /api/departments/{id}/curriculum` - 학과 교육과정 정보

### 전공 희망 조사

- `GET /api/surveys/summary` - 전공 희망 통계 요약
- `POST /api/surveys` - 전공 희망 설문 제출
- `GET /api/major-surveys/rounds/{round_id}` - 회차별 조사 결과

## 환경 변수

`.env` 파일을 생성하여 다음 변수를 설정할 수 있습니다:

```env
DATABASE_URL=sqlite:///./lions_dashboard.db
# 프로덕션에서는 PostgreSQL 사용:
# DATABASE_URL=postgresql://user:password@localhost/dbname
```

## 데이터베이스 스키마

주요 테이블:
- `colleges` - 단과대학 정보
- `departments` - 학과 정보
- `advisors` - 지도교수 정보
- `students` - 학생 정보
- `courses` - 과목 정보
- `course_enrollments` - 수강 이력
- `survey_rounds` - 설문 회차 정보
- `major_surveys` - 전공 희망 조사 제출 데이터

### 샘플 데이터

`seed_data.py` 스크립트는 다음과 같은 샘플 데이터를 생성합니다:
- 4개 단과대학 (라이언스 칼리지, 공과대학, 경영대학, 자연과학대학)
- 5개 학과 (자율전공학부, 컴퓨터공학과, 경영학과, 기계공학과, 전자공학과)
- 3명의 지도교수
- 50명의 학생 (LIONSE 분류, 1-2반)
- 7개 과목 (전공 및 교양)
- 수강 이력 및 전공 희망 조사 데이터

## 개발 가이드

### uv 패키지 관리

새로운 패키지 추가:
```bash
uv add package-name
```

개발 의존성 추가:
```bash
uv add --dev package-name
```

### 새로운 엔드포인트 추가

1. `models/schemas.py`에 Pydantic 모델 정의
2. `routers/` 디렉토리에 새로운 라우터 생성 또는 기존 라우터 수정
3. `main.py`에 라우터 등록 (필요시)

### 데이터베이스 모델 수정

1. `models/database.py`에서 SQLAlchemy 모델 수정
2. 기존 데이터베이스 삭제 후 재생성: `rm lions_dashboard.db && uv run python seed_data.py`
3. (프로덕션) Alembic을 사용한 마이그레이션 권장

## 구현된 기능

### ✅ 학생 관리
- 학생 목록 조회 (필터링: 학과, PRIDE, 분반, 학적 상태)
- 페이징 지원 (page, per_page)
- 학생 상세 정보 조회 (학과, 지도교수 정보 포함)
- 학생 수강 이력 조회 (총 학점 계산)
- 학생 전공 희망 조사 이력 조회
- 신규 학생 등록 (중복 검사 포함)

### ✅ 과목 및 교육과정
- 과목 목록 조회 (유형별, 학과별 필터)
- 전공 진입 필수 과목 목록
- 학과 리스트 (단과대학, 졸업 학점 정보 포함)
- 학과별 과목 조회
- 학과 교육과정 정보

### ✅ 전공 희망 조사
- 전공 희망 통계 요약 (전체 학생 수, 학과별 선호도, 참여율)
- 전공 희망 설문 제출 (중복 제출 방지)
- 회차별 조사 결과 조회 (페이징 지원)

## API 명세

자세한 API 명세는 `api_spec.md` 파일을 참고하세요.

모든 API 엔드포인트는 API 규격 문서에 맞춰 구현되었으며, CORS 설정이 포함되어 프론트엔드와의 연동이 가능합니다.

MIT License
