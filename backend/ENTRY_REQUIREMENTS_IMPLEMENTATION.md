# 전공진입요건 시스템 구현 문서

## 📋 개요

본 문서는 2026학번 기준 전공진입요건 시스템의 구현 내용을 설명합니다.

**구현 날짜:** 2026-01-29  
**구현 범위:** 데이터베이스 스키마, 샘플 데이터, API, 프론트엔드 표시

---

## 🗄️ 데이터베이스 스키마

### 1. DepartmentEntryRequirement (학과진입요건)

진입요건의 기본 정보를 저장하는 테이블입니다.

```python
class DepartmentEntryRequirement(Base):
    __tablename__ = "department_entry_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    admission_year = Column(Integer, nullable=False)  # 적용 학번 (2026 등)
    requirement_group = Column(Integer, nullable=False)  # 요건 그룹 번호
    target_grade_level = Column(Enum(GradeLevelEnum), nullable=False)  # 기준 성적: A, B, C
    required_count = Column(Integer, nullable=False)  # 필요한 과목 수
    requirement_text = Column(Text, nullable=False)  # 사용자 노출용 설명
    is_alert_required = Column(Boolean, default=False)  # 알림창 여부
    logic_operator = Column(String(10), default="AND")  # "AND" 또는 "OR"
    
    # Relationships
    department = relationship("Department")
    requirement_courses = relationship("RequirementCourse", cascade="all, delete-orphan")
    
    # Unique Constraint
    __table_args__ = (
        UniqueConstraint('department_id', 'admission_year', 'requirement_group'),
    )
```

**필드 설명:**

| 필드 | 타입 | 설명 | 예시 |
|-----|------|------|------|
| `department_id` | Integer | 학과 ID | 204 (전자공학부) |
| `admission_year` | Integer | 적용 학번 | 2026 |
| `requirement_group` | Integer | 요건 그룹 번호 | 1 |
| `target_grade_level` | Enum | 기준 성적 (A/B/C) | B (3.0 이상) |
| `required_count` | Integer | 필요 과목 수 | 2 |
| `requirement_text` | Text | 설명 문구 | "5개 과목 중 B 이상 2과목" |
| `is_alert_required` | Boolean | 알림창 표시 여부 | True |
| `logic_operator` | String | 논리 연산자 | "OR" |

---

### 2. RequirementCourse (요건 과목)

진입요건 대상 과목을 매핑하는 테이블입니다.

```python
class RequirementCourse(Base):
    __tablename__ = "requirement_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("department_entry_requirements.id"), nullable=False)
    course_code = Column(String(20), ForeignKey("courses.course_code"), nullable=False)
    
    # Relationships
    requirement = relationship("DepartmentEntryRequirement")
    course = relationship("Course")
```

**관계:**
- 1개의 `DepartmentEntryRequirement`는 여러 개의 `RequirementCourse`를 가질 수 있음
- Many-to-Many 관계 (진입요건 ↔ 과목)

---

## 📊 구현된 진입요건 데이터 (2026학번)

### 1. 전자공학부 (공학대학, dept_id: 204)

**조건:** OR 조건 (둘 중 하나만 충족하면 됨)

```
Option A: 5개 과목 중 A학점(4.0) 이상 1과목
   OR
Option B: 5개 과목 중 B학점(3.0) 이상 2과목
```

**대상 과목:**
- GEN2050: 확률과통계
- GEN2052: 미분적분학1
- GEN2053: 미분적분학2
- GEN0063: 일반물리학1
- GEN0064: 일반물리학2

**데이터 구조:**
```python
# Option A: A학점 1과목
{
    "department_id": 204,
    "admission_year": 2026,
    "requirement_group": 1,
    "target_grade_level": "A",
    "required_count": 1,
    "logic_operator": "OR",
    "requirement_text": "5개 과목 중 A(4.0) 이상 1과목"
}

# Option B: B학점 2과목
{
    "department_id": 204,
    "admission_year": 2026,
    "requirement_group": 1,
    "target_grade_level": "B",
    "required_count": 2,
    "logic_operator": "OR",
    "requirement_text": "5개 과목 중 B(3.0) 이상 2과목"
}
```

---

### 2. 산업경영공학과 (공학대학, dept_id: 207)

**조건:** AND 조건 (반드시 충족해야 함)

```
미분적분학1 과목을 C학점(2.0) 이상으로 이수
```

**대상 과목:**
- GEN2052: 미분적분학1

**데이터 구조:**
```python
{
    "department_id": 207,
    "admission_year": 2026,
    "requirement_group": 1,
    "target_grade_level": "C",
    "required_count": 1,
    "logic_operator": "AND",
    "requirement_text": "미분적분학1 C(2.0) 이상 필수"
}
```

---

### 3. 분자의약전공 (첨단융합대학, dept_id: 404)

**조건:** AND 조건

```
2개 과목 중 B학점(3.0) 이상 1과목
```

**대상 과목:**
- GEN0072: 일반생물학1
- GEN0073: 일반생물학2

**데이터 구조:**
```python
{
    "department_id": 404,
    "admission_year": 2026,
    "requirement_group": 1,
    "target_grade_level": "B",
    "required_count": 1,
    "logic_operator": "AND",
    "requirement_text": "2개 과목 중 B(3.0) 이상 1과목 필수"
}
```

---

### 4. 광고홍보학과 (커뮤니케이션&컬쳐대학, dept_id: 600)

**조건:** AND 조건

```
5개 과목 중 B학점(3.0) 이상 1과목
```

**대상 과목:**
- 커뮤니케이션론
- 광고원론
- 홍보원론
- 크리에이티브디자인
- 전략적커뮤니케이션

**데이터 구조:**
```python
{
    "department_id": 600,
    "admission_year": 2026,
    "requirement_group": 1,
    "target_grade_level": "B",
    "required_count": 1,
    "logic_operator": "AND",
    "requirement_text": "5개 과목 중 B(3.0) 이상 1과목 필수"
}
```

---

## 🔧 OR 조건 처리 방식

### 문제 상황

전자공학부처럼 "A학점 1개 OR B학점 2개" 같은 복합 조건을 어떻게 표현할까?

### 해결 방법

**같은 `requirement_group`에 여러 레코드를 생성하고 `logic_operator="OR"`로 설정**

```python
# 전자공학부의 경우
requirement_group = 1

# 레코드 1: A학점 1개
DepartmentEntryRequirement(
    department_id=204,
    requirement_group=1,  # 같은 그룹
    target_grade_level="A",
    required_count=1,
    logic_operator="OR"   # OR 조건
)

# 레코드 2: B학점 2개
DepartmentEntryRequirement(
    department_id=204,
    requirement_group=1,  # 같은 그룹
    target_grade_level="B",
    required_count=2,
    logic_operator="OR"   # OR 조건
)
```

### 평가 로직 (의사코드)

```python
def check_requirement_group(student, requirement_group):
    requirements = get_requirements_by_group(requirement_group)
    
    if requirements[0].logic_operator == "OR":
        # OR 조건: 하나라도 충족하면 통과
        for req in requirements:
            if check_single_requirement(student, req):
                return True
        return False
    
    else:  # AND
        # AND 조건: 모두 충족해야 통과
        for req in requirements:
            if not check_single_requirement(student, req):
                return False
        return True
```

---

## 🔗 API 엔드포인트

### 1. 커리큘럼 조회 (진입요건 포함)

**엔드포인트:**
```
GET /api/courses/curriculum?department_id={id}
```

**응답 예시:**
```json
{
  "curriculum": {
    "1학년": {
      "1학기": [
        {
          "course_id": 4,
          "course_code": "GEN2052",
          "course_name": "미분적분학1",
          "credits": 3,
          "course_type": "전공기초",
          "is_entry_requirement": true,  // ⭐ 진입요건 표시
          "is_recommended": false,
          "department_name": "산업경영공학전공"
        }
      ]
    }
  }
}
```

**처리 로직:**

```python
# backend/routers/courses.py

# 1. 진입요건 과목 조회
entry_requirement_courses = set()
requirements = db.query(DepartmentEntryRequirement).filter(
    DepartmentEntryRequirement.department_id == department_id
).all()

for req in requirements:
    for req_course in req.requirement_courses:
        entry_requirement_courses.add(req_course.course_code)

# 2. 커리큘럼 구성 시 플래그 설정
course_dict = {
    "course_code": course.course_code,
    "course_name": course.course_name,
    "is_entry_requirement": course.course_code in entry_requirement_courses,  # ⭐
    # ...
}
```

---

## 🎨 프론트엔드 표시

### 1. StudentDetailView.tsx - "수강필수" 배지

**위치:** 전공체계도에서 진입요건 과목에 배지 표시

```tsx
{course.is_entry_requirement && (
  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
    수강필수
  </span>
)}
```

**화면 예시:**
```
┌─────────────────────────────────────────┐
│ 1학년 1학기                              │
├─────────────────────────────────────────┤
│ 미분적분학1 (3학점)  [수강필수]          │
│ 일반물리학1 (3학점)  [수강필수]          │
│ 프로그래밍기초 (3학점)                   │
└─────────────────────────────────────────┘
```

---

### 2. CurriculumView.tsx - 학과별 커리큘럼 조회

**위치:** 관리자 뷰에서 학과 선택 시 커리큘럼 표시

```tsx
const AVAILABLE_DEPARTMENTS = [
  { id: 300, name: '컴퓨터학부' },
  { id: 303, name: '데이터인텔리전스전공' },
  { id: 304, name: '디자인컨버전스전공' },
  { id: 200, name: '건축학전공' },
  { id: 204, name: '전자공학부' },        // ⭐ 진입요건 있음
  { id: 207, name: '산업경영공학과' }     // ⭐ 진입요건 있음
];
```

---

## 📝 데이터 입력 방법

### seed_data.py에서 자동 생성

**위치:** `backend/seed_data.py` (lines 1000-1050)

```python
def create_entry_requirements(db: Session):
    """2026학번 진입요건 생성"""
    
    # 전자공학부 (OR 조건)
    req_elec_a = DepartmentEntryRequirement(
        department_id=DEPT_ELECTRONICS,
        admission_year=2026,
        requirement_group=1,
        target_grade_level=GradeLevelEnum.A,
        required_count=1,
        requirement_text="아래 5개 과목 중 성적 A(4.0) 이상 1과목 필수",
        is_alert_required=True,
        logic_operator="OR"
    )
    db.add(req_elec_a)
    db.flush()
    
    # 요건 과목 추가
    for course_code in ["GEN2050", "GEN2052", "GEN2053", "GEN0063", "GEN0064"]:
        req_course = RequirementCourse(
            requirement_id=req_elec_a.id,
            course_code=course_code
        )
        db.add(req_course)
    
    # ... (다른 학과들)
    
    db.commit()
```

**실행:**
```bash
# Docker 재시작 시 자동 실행
docker-compose down -v
docker-compose up -d

# 또는 수동 실행
cd backend
python seed_data.py
```

---

## 🧪 테스트 방법

### 1. 데이터베이스 확인

```sql
-- 진입요건 목록 조회
SELECT 
    der.id,
    d.name AS department,
    der.admission_year,
    der.requirement_group,
    der.target_grade_level,
    der.required_count,
    der.logic_operator,
    der.requirement_text
FROM department_entry_requirements der
JOIN departments d ON der.department_id = d.id
ORDER BY d.name, der.requirement_group;

-- 특정 학과의 요건 과목 조회
SELECT 
    c.course_code,
    c.course_name,
    der.requirement_text
FROM requirement_courses rc
JOIN courses c ON rc.course_code = c.course_code
JOIN department_entry_requirements der ON rc.requirement_id = der.id
WHERE der.department_id = 204  -- 전자공학부
ORDER BY c.course_code;
```

### 2. API 테스트

```bash
# 전자공학부 커리큘럼 조회
curl http://localhost:8080/api/courses/curriculum?department_id=204 | jq

# 진입요건 과목만 필터링
curl http://localhost:8080/api/courses/curriculum?department_id=204 | \
  jq '.curriculum[][] | .[] | select(.is_entry_requirement == true)'
```

**기대 결과:**
```json
{
  "course_code": "GEN2052",
  "course_name": "미분적분학1",
  "is_entry_requirement": true,
  ...
}
```

### 3. Python 스크립트로 확인

```bash
cd backend
python check_requirements.py
```

**출력 예시:**
```
총 5개 진입요건:

1. 전자공학부 (2026년)
   - 요구: 2 이상 1과목 (logic_operator=OR)
   - 설명: 5개 과목 중 A(4.0) 이상 1과목 필수
   - 과목 (5개): 확률과통계 (GEN2050), 미분적분학1 (GEN2052), ...

2. 산업경영공학과 (2026년)
   - 요구: 2 이상 1과목 (logic_operator=AND)
   - 설명: 미분적분학1 C(2.0) 이상 필수
   - 과목 (1개): 미분적분학1 (GEN2052)
```

---

## 🔍 알고리즘 연동 (향후 구현)

현재는 **진입요건 정의와 표시**만 구현되었습니다.  
다음 단계로 **평가 알고리즘**을 구현해야 합니다.

### 평가 알고리즘 (예정)

```python
def evaluate_entry_requirement(student_id: int, department_id: int) -> dict:
    """
    학생의 진입요건 충족 여부 평가
    
    Returns:
        {
            "is_satisfied": True/False,
            "score": 0-100,
            "details": [...]
        }
    """
    # 1. 학생의 수강 과목 + 성적 조회
    enrollments = get_student_enrollments(student_id)
    
    # 2. 진입요건 조회
    requirements = get_entry_requirements(department_id, admission_year)
    
    # 3. 각 requirement_group 평가
    for group in requirements:
        if group.logic_operator == "OR":
            # 하나라도 충족하면 통과
            if any(check_requirement(e, group) for e in enrollments):
                return {"is_satisfied": True, "score": 100}
        else:
            # 모두 충족해야 통과
            if not all(check_requirement(e, group) for e in enrollments):
                return {"is_satisfied": False, "score": 0}
    
    return {"is_satisfied": True, "score": 100}
```

**관련 문서:**
- [EVALUATION_ALGORITHM_DESIGN.md](./EVALUATION_ALGORITHM_DESIGN.md) - 평가 알고리즘 설계
- [EVALUATION_TESTING.md](./EVALUATION_TESTING.md) - 테스트 가이드

---

## 📚 참고 자료

### 관련 파일

**Backend:**
- `backend/models/database.py` - 테이블 정의 (lines 165-195)
- `backend/seed_data.py` - 샘플 데이터 생성 (lines 1000-1050)
- `backend/routers/courses.py` - API 엔드포인트 (lines 231-307)
- `backend/check_requirements.py` - 데이터 확인 스크립트

**Frontend:**
- `frontend/src/components/StudentDetailView.tsx` - 진입요건 배지 표시
- `frontend/src/components/CurriculumView.tsx` - 커리큘럼 조회

**데이터:**
- `backend/data/necessary.md` - 진입요건 원본 문서
- `backend/data/necessary.json` - 진입요건 JSON 정의

### 데이터베이스 ERD

```
┌─────────────────────────────┐
│ Department                  │
│ - id (PK)                   │
│ - name                      │
└─────────────────────────────┘
           ↑
           │ 1
           │
           │ N
┌─────────────────────────────┐
│ DepartmentEntryRequirement  │
│ - id (PK)                   │
│ - department_id (FK)        │
│ - admission_year            │
│ - requirement_group         │
│ - target_grade_level        │
│ - required_count            │
│ - logic_operator            │
│ - requirement_text          │
└─────────────────────────────┘
           ↑
           │ 1
           │
           │ N
┌─────────────────────────────┐       ┌─────────────────────────────┐
│ RequirementCourse           │   N   │ Course                      │
│ - id (PK)                   │ ───── │ - id (PK)                   │
│ - requirement_id (FK)       │   1   │ - course_code               │
│ - course_code (FK)          │       │ - course_name               │
└─────────────────────────────┘       └─────────────────────────────┘
```

---

## 🚀 향후 계획

### Phase 1: 진입요건 정의 ✅ 완료
- [x] 데이터베이스 스키마
- [x] 샘플 데이터 (4개 학과)
- [x] API 엔드포인트
- [x] 프론트엔드 표시

### Phase 2: 평가 알고리즘 ⏳ 진행 예정
- [ ] `services/evaluation_service.py` 구현
- [ ] 학생별 진입요건 충족도 계산
- [ ] `StudentRequirementStatus` 테이블 채우기
- [ ] 배치 평가 시스템

### Phase 3: 프론트엔드 연동 ⏳ 대기 중
- [ ] 평가 결과 조회 API
- [ ] 학생 상세 페이지에 평가 결과 표시
- [ ] 진입요건 충족/미충족 시각화

### Phase 4: AI 총평 ⏳ 대기 중
- [ ] LLM 연동
- [ ] 맞춤형 코멘트 생성
- [ ] AI 총평 저장 및 표시

---

## ❓ FAQ

### Q1. 새로운 학과의 진입요건을 추가하려면?

**A:** `seed_data.py`의 `create_entry_requirements()` 함수에 추가하고 DB 재시작

```python
# 새 학과 추가 예시
req_new = DepartmentEntryRequirement(
    department_id=NEW_DEPT_ID,
    admission_year=2026,
    requirement_group=1,
    target_grade_level=GradeLevelEnum.B,
    required_count=1,
    requirement_text="요건 설명",
    logic_operator="AND"
)
db.add(req_new)
db.flush()

# 과목 추가
for course_code in ["COURSE001", "COURSE002"]:
    rc = RequirementCourse(requirement_id=req_new.id, course_code=course_code)
    db.add(rc)
```

### Q2. OR 조건을 더 복잡하게 만들 수 있나? (예: "A 1개 OR B 2개 OR C 3개")

**A:** 가능합니다. 같은 `requirement_group`에 3개 레코드 생성

```python
# Option A: A학점 1개
req_a = DepartmentEntryRequirement(
    requirement_group=1,
    target_grade_level=GradeLevelEnum.A,
    required_count=1,
    logic_operator="OR"
)

# Option B: B학점 2개
req_b = DepartmentEntryRequirement(
    requirement_group=1,  # 같은 그룹
    target_grade_level=GradeLevelEnum.B,
    required_count=2,
    logic_operator="OR"
)

# Option C: C학점 3개
req_c = DepartmentEntryRequirement(
    requirement_group=1,  # 같은 그룹
    target_grade_level=GradeLevelEnum.C,
    required_count=3,
    logic_operator="OR"
)
```

### Q3. 학번별로 다른 요건을 어떻게 적용하나?

**A:** `admission_year` 필드로 구분

```python
# 2025학번
req_2025 = DepartmentEntryRequirement(
    department_id=204,
    admission_year=2025,
    # ...
)

# 2026학번 (다른 요건)
req_2026 = DepartmentEntryRequirement(
    department_id=204,
    admission_year=2026,
    # ...
)
```

평가 시 학생의 학번을 추출하여 해당 연도 요건을 조회합니다.

---

**작성일:** 2026-01-29  
**버전:** 1.0  
**작성자:** System  
**관련 문서:** 
- [EVALUATION_ALGORITHM_DESIGN.md](./EVALUATION_ALGORITHM_DESIGN.md)
- [EVALUATION_TESTING.md](./EVALUATION_TESTING.md)
- [요구사항_정리_0122.md](../요구사항_정리_0122.md)
