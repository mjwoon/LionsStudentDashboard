# 🏗️ Lions Student Dashboard - 전체 아키텍처

## 📐 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 (브라우저)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)                 │
│                         Port: 5173                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ DashboardView│  │StudentDetail │  │  AdminView   │          │
│  │  (통계/차트)  │  │  (평가결과)  │  │ (데이터관리) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│          └─────────────┬────api.ts────────────┘                 │
└────────────────────────┼────────────────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python)                     │
│                         Port: 8080                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API Routers (6개)                            │  │
│  │  students | courses | surveys | evaluation | admin | db  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Services (비즈니스 로직)                        │  │
│  │  EvaluationService | StudentService | AdminService       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Models (SQLAlchemy ORM)                     │  │
│  │  Student | Course | Department | Evaluation | Survey     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────┘
                         │ SQL
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Database (PostgreSQL + pgvector)                    │
│                         Port: 5432                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  11개 테이블: students, courses, departments, colleges,   │  │
│  │  course_enrollments, major_surveys, survey_rounds,        │  │
│  │  department_entry_requirements, requirement_courses,      │  │
│  │  student_requirement_status, advisors                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Redis (캐시/메시지 브로커)                     │
│                         Port: 6379                               │
│                   (AI 작업용 - 현재 미사용)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 주요 컴포넌트

### 1️⃣ Frontend (React + TypeScript)

**위치:** `frontend/src/`

**주요 컴포넌트:**
```
frontend/src/
├── App.tsx                    # 메인 앱, 뷰 전환
├── api.ts                     # API 클라이언트 (백엔드 통신)
├── main.tsx                   # React 진입점
└── components/
    ├── DashboardView.tsx      # 전체 통계 대시보드
    ├── StudentDetailView.tsx  # 학생 상세 정보 + 평가 결과
    ├── CurriculumView.tsx     # 커리큘럼 조회
    ├── AdminView.tsx          # 관리자 페이지
    └── DataUploadTab.tsx      # 데이터 업로드 UI
```

**기술 스택:**
- React 18 + TypeScript
- Tailwind CSS (스타일링)
- Vite (빌드 도구)
- Lucide React (아이콘)

**주요 기능:**
- ✅ 학생 목록 조회 및 검색
- ✅ 학생별 평가 결과 시각화 (6개 메트릭)
- ✅ 학과 선택 UI (단과대 → 학과)
- ✅ 커리큘럼 조회 (진입요건 배지 표시)
- ✅ 통계 대시보드 (전체 현황)
- ✅ 관리자 데이터 업로드

---

### 2️⃣ Backend (FastAPI + Python)

**위치:** `backend/`

**디렉토리 구조:**
```
backend/
├── main.py                    # FastAPI 앱 진입점
├── database.py                # DB 연결 및 세션 관리
├── seed_data.py              # 초기 데이터 시드
├── batch_evaluate_all.py     # 배치 평가 스크립트
├── models/
│   ├── database.py           # SQLAlchemy 모델 (11개 테이블)
│   └── schemas.py            # Pydantic 스키마
├── routers/
│   ├── students.py           # 학생 API
│   ├── courses.py            # 과목/커리큘럼 API
│   ├── surveys.py            # 전공희망조사 API
│   ├── evaluation.py         # 평가 API ⭐
│   ├── admin.py              # 관리자 API
│   └── dashboard.py          # 대시보드 통계 API
├── services/
│   ├── evaluation_service.py # 평가 알고리즘 ⭐
│   ├── student_service.py    # 학생 비즈니스 로직
│   └── admin_service.py      # 관리자 비즈니스 로직
├── admin/
│   └── admin_cli.py          # CLI 관리 도구
└── data/
    ├── sw.json               # 컴퓨터학부 커리큘럼
    ├── dataIntelli.json      # 데이터인텔리전스
    ├── designConverge.json   # 디자인컨버전스
    ├── arch.json             # 건축학
    ├── elec.json             # 전자공학부
    ├── ime.json              # 산업경영공학과
    ├── necessary.json        # 진입요건 필수과목
    └── recommended.json      # 권장과목
```

**기술 스택:**
- FastAPI (웹 프레임워크)
- SQLAlchemy (ORM)
- PostgreSQL (데이터베이스)
- Pydantic (데이터 검증)
- uv (패키지 관리)

---

### 3️⃣ Database Schema (PostgreSQL)

**11개 테이블 구조:**

```sql
┌─────────────────┐
│    colleges     │  # 단과대
├─────────────────┤
│ id (PK)         │
│ name            │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│  departments    │  # 학과/전공
├─────────────────┤
│ id (PK)         │
│ code            │
│ name            │
│ college_id (FK) │
└────────┬────────┘
         │ 1:N
         ├─────────────────┐
         ▼                 ▼
┌─────────────────┐ ┌──────────────────────────────┐
│    students     │ │ department_entry_requirements │ # 진입요건
├─────────────────┤ ├──────────────────────────────┤
│ id (PK)         │ │ id (PK)                      │
│ student_id      │ │ department_id (FK)           │
│ name            │ │ admission_year               │
│ department_id   │ │ requirement_group            │
│ current_gpa     │ │ target_grade_level (A/B/C)   │
│ ...             │ │ required_count               │
└────────┬────────┘ │ logic_operator (AND/OR)      │
         │          └────────┬─────────────────────┘
         │ 1:N              │ 1:N
         ▼                  ▼
┌─────────────────────┐ ┌──────────────────┐
│ course_enrollments  │ │ requirement_courses │
├─────────────────────┤ ├──────────────────┤
│ id (PK)             │ │ id (PK)          │
│ student_id (FK)     │ │ requirement_id   │
│ course_id (FK)      │ │ course_code (FK) │
│ grade (A+, B0, ...) │ └──────────────────┘
│ numeric_grade       │
└─────────┬───────────┘
          │ N:1
          ▼
┌─────────────────┐
│    courses      │  # 과목
├─────────────────┤
│ id (PK)         │
│ course_code     │
│ course_name     │
│ course_type     │
│ department_id   │
│ course_year     │
└─────────────────┘

┌───────────────────────────┐
│ student_requirement_status │ # 평가 결과 캐시 ⭐
├───────────────────────────┤
│ id (PK)                   │
│ student_id (FK)           │
│ department_id (FK)        │
│ gpa_score                 │ # 20%
│ required_courses_score    │ # 40%
│ recommended_completion    │ # 15%
│ recommended_grade         │ # 15%
│ curriculum_completion     │ # 10%
│ overall_score             │ # 종합 (0-100)
│ grade (A/B/C/D/F)         │
│ analysis_json (JSON)      │
│ ai_summary (TEXT)         │ # 미구현
│ calculated_at             │
└───────────────────────────┘
```

**데이터 볼륨:**
- Students: 303명
- Departments: 40개
- Courses: 수천 개
- Evaluations: 12,120개 (303 × 40)

---

### 4️⃣ API 엔드포인트

#### **Students API** (`/api/students`)
```
GET    /students                 # 학생 목록 (페이지네이션, 검색)
GET    /students/{student_id}    # 학생 상세 정보
GET    /students/{id}/courses    # 학생 수강 이력
POST   /students                 # 학생 생성
```

#### **Courses API** (`/api/courses`, `/api/departments`)
```
GET    /courses                              # 과목 목록
GET    /courses/entry-requirements           # 진입요건 조회
GET    /departments                          # 학과 목록
GET    /departments/{id}/courses             # 학과별 과목
GET    /departments/{id}/curriculum          # 커리큘럼 (진입요건 포함)
```

#### **Evaluation API** (`/api/evaluation`) ⭐ 핵심
```
GET    /student/{student_id}/department/{dept_id}
       → 특정 학생의 특정 학과 평가 결과
       → Query: force_recalculate=true (재계산)

GET    /student/{student_id}/all-departments
       → 학생의 모든 학과 평가 결과

POST   /batch/department/{dept_id}
       → 특정 학과에 대한 전체 학생 배치 평가
```

#### **Surveys API** (`/api/surveys`)
```
GET    /surveys/summary          # 전공희망조사 요약
POST   /surveys                  # 조사 제출
GET    /major-surveys/rounds/{id} # 특정 라운드 조사
```

#### **Admin API** (`/api/admin`)
```
POST   /upload/courses           # 과목 데이터 업로드
POST   /upload/students          # 학생 데이터 업로드
POST   /upload/enrollments       # 수강 데이터 업로드
```

#### **Dashboard API** (`/api/dashboard`)
```
GET    /stats                    # 전체 통계
```

---

## 🔄 데이터 흐름

### **평가 시스템 워크플로우:**

```
1️⃣ 데이터 준비
   seed_data.py 실행
   ↓
   DB에 학생/과목/수강 데이터 삽입

2️⃣ 배치 평가
   batch_evaluate_all.py 실행
   ↓
   EvaluationService가 303명 × 40학과 평가
   ↓
   StudentRequirementStatus에 12,120개 레코드 저장

3️⃣ 프론트엔드 조회
   사용자가 학과 선택
   ↓
   GET /api/evaluation/student/{id}/department/{dept_id}
   ↓
   캐시된 평가 결과 즉시 반환 (빠름)
   ↓
   6개 메트릭 + 종합 점수 표시
```

### **평가 알고리즘 (5개 메트릭):**

```python
# services/evaluation_service.py

1. GPA 점수 (20%)
   student.current_gpa / 4.5 * 100

2. 필수과목 학점 (40%) ⭐ 가장 중요
   - DepartmentEntryRequirement 조회
   - OR/AND 조건 체크
   - A/B/C 등급 요구사항 확인

3. 권장과목 이수도 (15%)
   - recommended.json 기반
   - 이수한 과목 수 / 전체 권장과목 수

4. 권장과목 학점 (15%)
   - 권장과목 평균 성적

5. 교육과정 완성도 (10%)
   - 1학년 전공과목 이수 비율

종합 점수 = 가중 평균 (0-100점)
등급 = A/B/C/D/F (90/80/70/60 기준)
```

---

## 🐳 Docker 컨테이너 구성

```yaml
services:
  db (PostgreSQL)      : 5432  # pgvector 지원
  redis                : 6379  # AI용 (미사용)
  backend (FastAPI)    : 8080  # Python + uv
  frontend (React)     : 5173  # Vite dev server
```

**볼륨:**
- `postgres_data`: DB 영구 저장
- `backend/app`: 코드 핫 리로드
- `frontend/app`: 코드 핫 리로드

---

## 📊 주요 기능 흐름도

### **학생 평가 조회:**
```
User → Frontend (StudentDetailView)
         ↓ pathwayDept 변경
         ↓ useEffect 트리거
       api.evaluation.getStudentEvaluation()
         ↓ GET /api/evaluation/student/{id}/department/{dept_id}
       Backend (evaluation.py)
         ↓ 캐시 확인 (StudentRequirementStatus)
         ↓ 있으면 즉시 반환
       Frontend
         ↓ setEvaluation(result)
         ↓ 6개 메트릭 Progress Bar 렌더링
       User ← 평가 결과 확인
```

### **배치 평가:**
```
Admin → CLI 또는 직접 실행
         ↓ docker exec backend uv run python batch_evaluate_all.py
       EvaluationService
         ↓ for student in all_students:
         ↓   for dept in all_departments:
         ↓     calculate_5_metrics()
         ↓     save_to_db()
       StudentRequirementStatus
         ↓ 12,120개 레코드 생성/업데이트
       Complete ✅
```

---

## 🎨 프론트엔드 라우팅

```typescript
App.tsx
  └─ activeView 상태 (dashboard | student | admin)
      │
      ├─ dashboard → DashboardView.tsx
      │               ↓ 통계, 차트
      │
      ├─ student → StudentDetailView.tsx
      │             ↓ 탭 시스템 (기본정보 | 이수과목 | 희망전공조사 | 희망전공진입)
      │             ↓ pathwayDept 선택
      │             ↓ Evaluation API 호출
      │             ↓ 6개 메트릭 표시
      │
      └─ admin → AdminView.tsx
                  ↓ DataUploadTab
                  ↓ 과목/학생/수강 데이터 업로드
```

---

## 🔐 보안 & 성능

**보안:**
- ⚠️ CORS 모든 오리진 허용 (개발 환경)
- ⚠️ 인증/인가 미구현

**성능 최적화:**
- ✅ 사전계산 방식 (배치 평가)
- ✅ DB 인덱싱 (student_id, department_id)
- ✅ SQLAlchemy 쿼리 최적화
- ⚠️ 캐싱 전략 부족 (Redis 미활용)

---

## 📈 확장성

**현재 상태:**
- 303명 학생 ✅
- 40개 학과 ✅
- 12,120개 평가 ✅

**확장 가능성:**
- 학생 수 증가: DB 인덱싱으로 대응 가능
- 학과 수 증가: 배치 평가 시간만 증가 (선형)
- AI 총평: Redis + Worker 패턴 준비됨 (미구현)

---

## 🚀 배포 전략

**현재:**
- Docker Compose (로컬 개발)

**프로덕션 권장:**
1. Kubernetes 또는 Docker Swarm
2. PostgreSQL RDS
3. Redis ElastiCache
4. CloudFront (프론트엔드)
5. ALB (백엔드 로드밸런싱)

---

## 🎯 핵심 강점

1. **명확한 계층 분리**: Frontend ↔ API ↔ Service ↔ Model ↔ DB
2. **확장 가능한 구조**: 새 학과/메트릭 추가 용이
3. **사전계산 전략**: 빠른 응답 시간
4. **타입 안정성**: TypeScript + Pydantic
5. **컨테이너화**: 일관된 환경

---

## 📝 실행 방법

### 초기 설정
```bash
# 1. Docker 컨테이너 실행
docker-compose up -d

# 2. 데이터베이스 초기화 및 시드 데이터 삽입
docker exec fastapi_backend uv run python seed_data.py

# 3. 배치 평가 실행 (12,120개 평가)
docker exec fastapi_backend uv run python batch_evaluate_all.py
```

### 접속
- **프론트엔드**: http://localhost:5173
- **백엔드 API**: http://localhost:8080
- **API 문서**: http://localhost:8080/docs

---

이 아키텍처는 **학생 평가 시스템**에 최적화되어 있으며, 현재 실사용 가능한 상태입니다! 🎉
