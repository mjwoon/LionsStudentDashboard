# 희망전공진입 평가 알고리즘 설계서

## 📊 전체 아키텍처

```
[학생 수강 데이터] + [진입요건 데이터] 
           ↓
    [평가 알고리즘 엔진]
           ↓
    [평가 결과 테이블 저장]
           ↓
    [프론트엔드 표시]
```

---

## 🎯 평가 항목 (6개 점수)

현재 DB 스키마(`StudentRequirementStatus`)에 이미 정의된 평가 항목:

### 1. `gpa_score` (0-100점)
- **설명:** 전체 평점 기반 점수
- **계산 방식:** 
  - 4.5 만점 기준: `(현재 평점 / 4.5) * 100`
  - 예시: 평점 4.0 → 88.9점, 평점 3.5 → 77.8점

### 2. `required_courses_score` (0-100점) ⭐ **핵심**
- **설명:** 진입요건 필수과목 충족도
- **계산 방식:**
  - 완전 충족: 100점
  - 부분 충족: 비율에 따라 0-80점
  - 미충족: 0점
- **예시:**
  - 전자공학부: 5개 과목 중 A학점 1개 OR B학점 2개
  - 학생이 A학점 1개 달성 → 100점

### 3. `recommended_completion_score` (0-100점)
- **설명:** 권장과목 이수 여부
- **계산 방식:** `(수강한 권장과목 수 / 전체 권장과목 수) * 100`
- **예시:**
  - 권장 20과목 중 15개 수강 → 75점

### 4. `recommended_grade_score` (0-100점)
- **설명:** 권장과목의 학점 수준
- **계산 방식:** `(권장과목 평균 학점 / 4.5) * 100`
- **예시:**
  - 권장과목 평균 학점 3.8/4.5 → 84.4점

### 5. `curriculum_completion_score` (0-100점)
- **설명:** 학과 전공체계도 완성도
- **계산 방식:** 학년별 필수 과목 이수율
- **예시:**
  - 1-2학년 전공기초 10개 중 8개 수강 → 80점

### 6. `overall_score` (0-100점)
- **설명:** 위 5개 항목의 가중 평균
- **계산 방식:** 
  ```
  overall_score = (
      required_courses_score * 0.40 +
      gpa_score * 0.20 +
      recommended_completion_score * 0.15 +
      recommended_grade_score * 0.15 +
      curriculum_completion_score * 0.10
  )
  ```

---

## ⚙️ 핵심 알고리즘: required_courses_score 계산

### 전자공학부 진입요건 예시 (2026학번)

**조건:**
```
5개 과목 중:
  Option A: A학점(4.0) 이상 1과목
  OR
  Option B: B학점(3.0) 이상 2과목

과목 목록:
- GEN2050: 확률과통계
- GEN2052: 미분적분학1
- GEN2053: 미분적분학2
- GEN0063: 일반물리학1
- GEN0064: 일반물리학2
```

### 알고리즘 의사코드

```python
def calculate_required_courses_score(student_id, department_id, admission_year):
    """
    진입요건 필수과목 충족도 계산
    
    Returns:
        int: 0-100 사이의 점수
    """
    # 1단계: 학생의 입학년도로 진입요건 조회
    requirements = db.query(DepartmentEntryRequirement).filter(
        department_id=department_id,
        admission_year=admission_year
    ).all()
    
    if not requirements:
        return None  # 진입요건 미정의
    
    # 2단계: 학생의 수강 과목 + 성적 조회
    enrollments = db.query(Enrollment).filter(
        student_id=student_id
    ).all()
    
    # 성적 딕셔너리 생성: {course_code: numeric_grade}
    grades = {e.course_code: e.numeric_grade for e in enrollments}
    
    # 3단계: 각 requirement_group 별로 충족 여부 체크
    group_results = []
    
    for req_group in group_by_requirement_group(requirements):
        if req_group.logic_operator == "OR":
            # OR 조건: 하나라도 만족하면 통과
            satisfied = check_or_condition(req_group, grades)
            group_results.append(satisfied)
            
        elif req_group.logic_operator == "AND":
            # AND 조건: 모두 만족해야 통과
            satisfied = check_and_condition(req_group, grades)
            group_results.append(satisfied)
    
    # 4단계: 최종 점수 계산
    if all(group_results):
        return 100  # 완전 충족
    elif any(group_results):
        return 60  # 부분 충족
    else:
        # 미충족 - 진행률 기반 부분 점수
        return calculate_partial_score(requirements, grades)


def check_or_condition(req_group, grades):
    """
    OR 조건 체크
    
    예시: 5개 과목 중 A학점 1개 OR B학점 2개
    """
    requirement_courses = get_requirement_courses(req_group.id)
    
    # Option A: A학점 이상 과목 수 체크
    a_grade_count = sum(
        1 for course_code in requirement_courses
        if grades.get(course_code, 0) >= req_group.min_grade
    )
    
    if a_grade_count >= req_group.required_count:
        return True
    
    # Option B: B학점 조건이 있다면 별도 체크
    # (현재 스키마로는 표현 제한 - 추후 개선 필요)
    
    return False


def check_and_condition(req_group, grades):
    """
    AND 조건 체크
    
    예시: 모든 과목을 C학점 이상으로 이수
    """
    requirement_courses = get_requirement_courses(req_group.id)
    
    satisfied_count = sum(
        1 for course_code in requirement_courses
        if grades.get(course_code, 0) >= req_group.min_grade
    )
    
    return satisfied_count >= req_group.required_count


def calculate_partial_score(requirements, grades):
    """
    미충족 시 부분 점수 계산
    
    Returns:
        int: 0-50 사이의 점수
    """
    total_courses = len(get_all_requirement_courses(requirements))
    completed_courses = sum(
        1 for course_code in get_all_requirement_courses(requirements)
        if course_code in grades
    )
    
    # 수강 비율 기반 부분 점수
    completion_ratio = completed_courses / total_courses
    return int(completion_ratio * 50)
```

---

## 📋 복잡한 조건 처리 예시

### 예시 1: 전자공학부 (OR 조건)

**학생 A:**
```python
수강 과목:
- GEN2052 (미분적분학1): A0 (4.0)
- GEN0063 (일반물리학1): B+ (3.5)

평가 결과:
→ Option A 충족 (A학점 1개 ✅)
→ required_courses_score = 100점
```

**학생 B:**
```python
수강 과목:
- GEN2052 (미분적분학1): B+ (3.5)
- GEN0063 (일반물리학1): B0 (3.0)

평가 결과:
→ Option A 미충족 (A학점 0개 ❌)
→ Option B 충족 (B학점 2개 ✅)
→ required_courses_score = 100점
```

**학생 C:**
```python
수강 과목:
- GEN2052 (미분적분학1): C+ (2.5)

평가 결과:
→ Option A 미충족 (A학점 0개 ❌)
→ Option B 미충족 (B학점 0개 ❌)
→ 부분 점수: 5개 중 1개 수강 = 10점
→ required_courses_score = 10점
```

### 예시 2: 산업경영공학과 (AND 조건)

**조건:**
```
1개 과목을 C학점(2.0) 이상으로 이수
- GEN2052: 미분적분학1
```

**학생 D:**
```python
수강 과목:
- GEN2052 (미분적분학1): B0 (3.0)

평가 결과:
→ 조건 충족 (C학점 이상 ✅)
→ required_courses_score = 100점
```

**학생 E:**
```python
수강 과목:
- GEN2052 (미분적분학1): D+ (1.5)

평가 결과:
→ 조건 미충족 (C학점 미만 ❌)
→ 수강은 했으나 학점 부족 = 30점
→ required_courses_score = 30점
```

---

## 🗄️ 데이터 구조

### 입력 데이터

#### 1. DepartmentEntryRequirement 테이블
```python
{
    "id": 1,
    "department_id": 204,  # 전자공학부
    "admission_year": 2026,
    "requirement_group": 1,
    "target_grade_level": 2,
    "required_count": 1,
    "min_grade": 4.0,  # A학점
    "logic_operator": "OR"
}
```

#### 2. RequirementCourse 테이블
```python
{
    "id": 1,
    "requirement_id": 1,
    "course_code": "GEN2052"
}
```

#### 3. Enrollment 테이블 (학생 수강 데이터)
```python
{
    "id": 100,
    "student_id": 12345,
    "course_code": "GEN2052",
    "grade": "A0",
    "numeric_grade": 4.0,
    "semester": "2024-1",
    "year": 2024
}
```

### 출력 데이터

#### StudentRequirementStatus 테이블
```python
{
    "id": 1,
    "student_id": 12345,
    "department_id": 204,
    "is_satisfied": True,
    
    # 점수 필드
    "gpa_score": 85.0,
    "required_courses_score": 100.0,
    "recommended_completion_score": 75.0,
    "recommended_grade_score": 82.0,
    "curriculum_completion_score": 70.0,
    "overall_score": 87.5,
    
    # 상세 분석 데이터
    "analysis_json": {
        "entry_requirements": {
            "status": "satisfied",
            "completed_requirements": ["Option A: A학점 1개"],
            "details": [
                {
                    "course_code": "GEN2052",
                    "course_name": "미분적분학1",
                    "grade": "A0",
                    "numeric_grade": 4.0,
                    "satisfied": True
                },
                {
                    "course_code": "GEN0063",
                    "course_name": "일반물리학1",
                    "grade": "B+",
                    "numeric_grade": 3.5,
                    "satisfied": False
                }
            ]
        },
        "gpa": {
            "current_gpa": 3.82,
            "max_gpa": 4.5
        },
        "recommended_courses": {
            "total": 20,
            "completed": 15,
            "completion_rate": 0.75
        }
    },
    
    "ai_summary": null,  # Phase 3에서 구현
    "calculated_at": "2026-01-29T12:00:00"
}
```

---

## 🚀 구현 단계

### Phase 1: 평가 엔진 개발 (1-2일)

**파일 구조:**
```
backend/services/evaluation_service.py
├── calculate_gpa_score(student_id) → float
├── calculate_required_courses_score(student_id, dept_id, admission_year) → float ⭐
├── calculate_recommended_completion_score(student_id, dept_id) → float
├── calculate_recommended_grade_score(student_id, dept_id) → float
├── calculate_curriculum_completion_score(student_id, dept_id) → float
├── calculate_overall_score(...) → float
└── evaluate_student_for_department(student_id, dept_id) → StudentRequirementStatus
```

**핵심 함수:**
```python
def evaluate_student_for_department(student_id: int, department_id: int, db: Session):
    """
    학생 1명에 대한 특정 학과 평가 수행
    
    Returns:
        StudentRequirementStatus: 평가 결과 객체
    """
    # 학생 정보 조회
    student = db.query(Student).filter(Student.id == student_id).first()
    admission_year = get_admission_year_from_student_id(student.student_id)
    
    # 6개 점수 계산
    gpa_score = calculate_gpa_score(student_id, db)
    required_score = calculate_required_courses_score(student_id, department_id, admission_year, db)
    recommended_comp = calculate_recommended_completion_score(student_id, department_id, db)
    recommended_grade = calculate_recommended_grade_score(student_id, department_id, db)
    curriculum_score = calculate_curriculum_completion_score(student_id, department_id, db)
    overall = calculate_overall_score(gpa_score, required_score, recommended_comp, recommended_grade, curriculum_score)
    
    # 충족 여부 판단
    is_satisfied = required_score >= 100 and overall >= 70
    
    # 분석 JSON 생성
    analysis_json = build_analysis_json(student_id, department_id, db)
    
    # DB에 저장 또는 업데이트
    status = db.query(StudentRequirementStatus).filter(
        StudentRequirementStatus.student_id == student_id,
        StudentRequirementStatus.department_id == department_id
    ).first()
    
    if status:
        # 업데이트
        status.gpa_score = gpa_score
        status.required_courses_score = required_score
        status.recommended_completion_score = recommended_comp
        status.recommended_grade_score = recommended_grade
        status.curriculum_completion_score = curriculum_score
        status.overall_score = overall
        status.is_satisfied = is_satisfied
        status.analysis_json = analysis_json
        status.calculated_at = datetime.utcnow()
    else:
        # 신규 생성
        status = StudentRequirementStatus(
            student_id=student_id,
            department_id=department_id,
            gpa_score=gpa_score,
            required_courses_score=required_score,
            recommended_completion_score=recommended_comp,
            recommended_grade_score=recommended_grade,
            curriculum_completion_score=curriculum_score,
            overall_score=overall,
            is_satisfied=is_satisfied,
            analysis_json=analysis_json
        )
        db.add(status)
    
    db.commit()
    db.refresh(status)
    
    return status
```

### Phase 2: 배치 계산 시스템 (1일)

**파일:** `backend/admin_cli.py`

**추가 명령어:**
```bash
# 전체 학생 × 전체 학과 평가
python admin_cli.py evaluate-all

# 특정 학생만 평가
python admin_cli.py evaluate-student --student-id 20260001

# 특정 학과만 평가
python admin_cli.py evaluate-department --department-id 204
```

**구현:**
```python
@app.command()
def evaluate_all():
    """모든 학생에 대해 모든 학과 진입요건 평가 수행"""
    db = SessionLocal()
    
    # 진입요건이 정의된 학과 목록
    departments_with_requirements = db.query(DepartmentEntryRequirement.department_id).distinct().all()
    dept_ids = [d[0] for d in departments_with_requirements]
    
    # 모든 학생 조회
    students = db.query(Student).all()
    
    total = len(students) * len(dept_ids)
    processed = 0
    
    print(f"평가 시작: {len(students)}명 × {len(dept_ids)}개 학과 = {total}건")
    
    for student in students:
        for dept_id in dept_ids:
            try:
                evaluate_student_for_department(student.id, dept_id, db)
                processed += 1
                
                if processed % 10 == 0:
                    print(f"진행률: {processed}/{total} ({processed/total*100:.1f}%)")
                    
            except Exception as e:
                print(f"오류 발생 - 학생 {student.student_id}, 학과 {dept_id}: {e}")
    
    print(f"평가 완료: {processed}건 처리됨")
    db.close()
```

### Phase 3: API 엔드포인트 (0.5일)

**파일:** `backend/routers/evaluation.py` (신규 생성)

**엔드포인트:**
```python
@router.get("/students/{student_id}/evaluation")
async def get_student_evaluation(
    student_id: str,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    학생의 전공 평가 결과 조회
    
    - department_id가 없으면 모든 학과 평가 결과 반환
    - department_id가 있으면 해당 학과만 반환
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    query = db.query(StudentRequirementStatus).filter(
        StudentRequirementStatus.student_id == student.id
    )
    
    if department_id:
        query = query.filter(StudentRequirementStatus.department_id == department_id)
    
    results = query.all()
    
    return {
        "student_id": student_id,
        "student_name": student.name,
        "evaluations": [
            {
                "department_id": r.department_id,
                "department_name": r.department.name,
                "is_satisfied": r.is_satisfied,
                "scores": {
                    "gpa": float(r.gpa_score) if r.gpa_score else None,
                    "required_courses": float(r.required_courses_score) if r.required_courses_score else None,
                    "recommended_completion": float(r.recommended_completion_score) if r.recommended_completion_score else None,
                    "recommended_grade": float(r.recommended_grade_score) if r.recommended_grade_score else None,
                    "curriculum_completion": float(r.curriculum_completion_score) if r.curriculum_completion_score else None,
                    "overall": float(r.overall_score) if r.overall_score else None
                },
                "analysis": r.analysis_json,
                "ai_summary": r.ai_summary,
                "calculated_at": r.calculated_at
            }
            for r in results
        ]
    }
```

### Phase 4: 프론트엔드 연동 (1일)

**파일:** `frontend/src/components/StudentDetailView.tsx`

**UI 구조:**
```tsx
<div className="evaluation-section">
  <h3>희망전공 진입요건 평가</h3>
  
  {/* 학과 선택 드롭다운 */}
  <select onChange={handleDepartmentChange}>
    <option value="204">전자공학부</option>
    <option value="207">산업경영공학과</option>
    {/* ... */}
  </select>
  
  {/* 종합 점수 */}
  <div className="overall-score">
    <CircularProgress value={evaluation.overall_score} />
    <span>{evaluation.is_satisfied ? '✅ 진입요건 충족' : '❌ 미충족'}</span>
  </div>
  
  {/* 세부 점수 */}
  <div className="detailed-scores">
    <ScoreBar label="필수과목 충족도" score={evaluation.required_courses_score} />
    <ScoreBar label="전체 학점" score={evaluation.gpa_score} />
    <ScoreBar label="권장과목 이수" score={evaluation.recommended_completion_score} />
    <ScoreBar label="권장과목 학점" score={evaluation.recommended_grade_score} />
    <ScoreBar label="교육과정 완성도" score={evaluation.curriculum_completion_score} />
  </div>
  
  {/* 상세 분석 */}
  <div className="analysis-details">
    {evaluation.analysis.entry_requirements.details.map(course => (
      <div key={course.course_code}>
        {course.course_name}: {course.grade} 
        {course.satisfied ? '✅' : '❌'}
      </div>
    ))}
  </div>
  
  {/* AI 총평 */}
  {evaluation.ai_summary && (
    <div className="ai-summary">
      <h4>AI 진단</h4>
      <p>{evaluation.ai_summary}</p>
    </div>
  )}
</div>
```

---

## ⚠️ 핵심 난이도 포인트

### 1. 복잡한 논리 연산 처리
**문제:**
- "5개 중 A학점 1개 OR B학점 2개" 같은 복합 조건

**해결 방안:**
- `requirement_group` 필드로 그룹 분리
- 각 그룹마다 `logic_operator` 지정
- OR 조건은 여러 행으로 분리하여 저장

**현재 스키마 제약:**
- "A학점 1개 OR B학점 2개"를 하나의 테이블로 표현하기 어려움
- → 추후 개선: `min_grade_alt`, `required_count_alt` 필드 추가 고려

### 2. 학번별 조건 분기
**문제:**
- 2025학번과 2026학번의 진입요건이 다름

**해결 방안:**
```python
def get_admission_year_from_student_id(student_id: str) -> int:
    """
    학번에서 입학년도 추출
    예: "20260001" → 2026
    """
    return int(student_id[:4])

# 평가 시 학생의 입학년도로 진입요건 조회
admission_year = get_admission_year_from_student_id(student.student_id)
requirements = db.query(DepartmentEntryRequirement).filter(
    admission_year=admission_year
).all()
```

### 3. 부분 충족 점수 계산
**문제:**
- 완전 미충족: 0점
- 부분 충족: 비율에 따라 차등 점수
- 완전 충족: 100점

**해결 방안:**
```python
def calculate_partial_score(completed, required, max_score=50):
    """
    부분 충족 시 점수 계산
    
    Args:
        completed: 완료한 항목 수
        required: 필요한 항목 수
        max_score: 부분 점수 최대값
    """
    if completed >= required:
        return 100  # 완전 충족
    else:
        ratio = completed / required
        return int(ratio * max_score)  # 부분 점수
```

### 4. 성적 변환 로직
**문제:**
- 문자 성적 → 숫자 변환

**해결 방안:**
```python
GRADE_CONVERSION = {
    'A+': 4.5, 'A0': 4.0, 'A-': 3.7,
    'B+': 3.5, 'B0': 3.0, 'B-': 2.7,
    'C+': 2.5, 'C0': 2.0, 'C-': 1.7,
    'D+': 1.5, 'D0': 1.0, 'D-': 0.7,
    'F': 0.0
}

def grade_to_numeric(grade: str) -> float:
    return GRADE_CONVERSION.get(grade, 0.0)
```

---

## 📈 예상 성능

### 단일 평가 성능
- **학생 1명 × 학과 1개:** ~50ms
  - DB 조회: 20ms
  - 계산: 20ms
  - DB 저장: 10ms

### 전체 배치 성능
- **300명 × 6개 학과 = 1,800건**
  - 순차 처리: ~90초
  - 병렬 처리 (추후): ~20초

### 프론트엔드 조회 성능
- **사전 계산된 결과 조회:** ~5ms
  - 실시간 계산 대비 10배 빠름

---

## ✅ 구현 우선순위

### 1순위 (핵심)
- ✅ `calculate_required_courses_score()` - 진입요건 충족도
- ✅ `evaluate_student_for_department()` - 통합 평가 함수

### 2순위 (기본)
- ✅ `calculate_gpa_score()` - 전체 학점 점수
- ✅ `calculate_overall_score()` - 종합 점수

### 3순위 (부가)
- ⏸️ `calculate_recommended_completion_score()` - 권장과목 이수
- ⏸️ `calculate_recommended_grade_score()` - 권장과목 학점
- ⏸️ `calculate_curriculum_completion_score()` - 교육과정 완성도

### 4순위 (향후)
- ⏸️ AI 총평 생성 (LLM 연동)
- ⏸️ 배치 스케줄링 (자동 재계산)
- ⏸️ 알림 시스템 (진입요건 충족 시 알림)

---

## 🔄 다음 단계

1. **Phase 1 구현:** `backend/services/evaluation_service.py` 생성
2. **테스트:** 샘플 학생 데이터로 알고리즘 검증
3. **Phase 2 구현:** 배치 계산 시스템
4. **Phase 3 구현:** API 엔드포인트
5. **Phase 4 구현:** 프론트엔드 UI

---

**작성일:** 2026-01-29  
**버전:** 1.0  
**상태:** 설계 완료, 구현 대기중
