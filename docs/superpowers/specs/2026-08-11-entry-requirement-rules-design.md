# 진입요건 규칙 평가 (Entry Requirement Rules) — 설계 스펙

- **날짜**: 2026-08-11
- **대상**: `packages/lions-core/lions_core/` 평가 서비스 (Phase 7b)
- **성격**: 동작 변경(behavior-changing). 진입요건 점수 산식이 바뀐다.
- **선행**: Phase 0–6(순수 리팩토링, 커밋 `3433fa7`), Phase 7a(admission_year 활성화).

## 1. 배경 / 문제

`DepartmentEntryRequirement`는 정교한 진입요건 규칙 필드를 스키마에 갖고 있으나 평가 로직이 이를 **전혀 사용하지 않는다**:

- `requirement_group` — 요건 그룹 구분
- `target_grade_level` (Enum A/B/C) — 통과 최소 성적
- `required_count` — 그룹 내 필요한 과목 수
- `logic_operator` (AND/OR) — 그룹 결합자

현재 `entry_requirement_score`는 단순히 "필수과목 이수 개수 / 전체 필수과목 수 × 100"만 계산하고, 성적 기준·필요 개수·그룹 구조를 무시한다. 스키마가 약속한 규칙을 서비스가 이행하지 않아 요건 규칙을 표현할 수 없다.

## 2. 실데이터 근거

`group5_requirements_recs.csv` (ELEC 2026):

| group | target_grade_level | required_count | 후보과목 | requirement_text |
|---|---|---|---|---|
| 1 | A (≥4.0) | 1 | ELE3037, GEN2052, GEN0063, GEN2053, GEN0064 | "5개 과목 중 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수" |
| 2 | B (≥3.0) | 2 | (동일 5과목) | (동일) |

하나의 요건이 **(A+ 1과목) OR (B+ 2과목)** 두 분기로 표현되고, 스키마는 이를 group1/group2로 분해했다.

## 3. 확정된 규칙 의미 (도메인 결정)

1. **그룹 충족 조건**: 그룹의 후보과목 중 학생이 **성적 numeric ≥ `GRADE_LEVEL_MINIMUM[target_grade_level]`** 로 이수한 과목이 **`required_count`개 이상**이면 그 그룹은 충족.
   - `GRADE_LEVEL_MINIMUM`: A→4.0, B→3.0, C→2.0 (requirement_text의 "A(4.0)/B(3.0) 이상"과 일치).
2. **그룹 결합**: **모든 그룹을 OR** — 어느 그룹이든 하나라도 충족하면 진입요건 통과. `logic_operator`는 사용하지 않는다.
3. **점수(부분, 0~100)**: 각 그룹의 진행률 `min(자격과목수 / required_count, 1.0) × 100` 을 계산하고, **그룹 간 최댓값**을 진입요건 점수로 한다(OR = 최선의 대안 기준 진행도).
4. **요건 없음**: 해당 학과·입학년도에 진입요건 그룹이 없으면 점수 100.0 (현행 유지).
5. 이 점수는 기존대로 `overall_score`의 40% 가중으로 들어간다(`EVALUATION_WEIGHTS["entry_requirement"]`).

## 4. 성적 비교 / 매칭 규칙 (확정)

- 학생 과목의 numeric 성적: **`StudentCourse.numeric_grade` 우선**, 없으면 **`GRADE_TO_NUMERIC[grade]` 폴백**, 둘 다 없으면 0.0(미자격).
- 후보과목 매칭: **`course_code` 기준**(진입요건은 특정 과목 지정).
- **유사과목 대체(Neo4j) 미적용** — 진입요건은 정밀 매칭 유지(현행 동작과 동일). 유사 대체는 권장/교육과정 메트릭에만 적용된다.

## 5. 컴포넌트 / 인터페이스

### 5.1 완료과목 정보 확장
`EvaluationService._get_student_completed_courses` 의 `details` 항목에 **`numeric_grade`** 추가:
```
{course_code, course_name, grade, credits, numeric_grade}
```
`numeric_grade`는 4.1 규칙으로 산출.

### 5.2 요건 그룹 조회 (신규)
`EvaluationService._get_entry_requirement_groups(department_id, admission_year) -> List[Dict]`
```
[
  {
    "group": 1,
    "target_min": 4.0,          # GRADE_LEVEL_MINIMUM[target_grade_level]
    "required_count": 1,
    "candidate_codes": {"ELE3037", "GEN2052", ...},
  },
  ...
]
```
- `DepartmentEntryRequirement` (department_id, admission_year 필터=7a 재사용) + `RequirementCourse` 조인.
- admission_year=None이면 전체 연도(레거시 호환).

### 5.3 순수 점수 함수 (신규, `scoring.py`)
`entry_requirement_score_by_rules(groups, student_completed_courses) -> float`
- `Session`·DB 무의존 순수 함수. `groups`(5.2 형태) + `completed`(numeric_grade 포함) → 0~100.
- 로직: 그룹별 자격과목수 = 후보 중 `numeric_grade >= target_min` 인 이수과목 수 → 진행률 → 그룹 간 최댓값. 그룹 없으면 100.0.
- 기존 `scoring.entry_requirement_score`(개수 비율)는 제거 또는 신규 함수로 대체.

### 5.4 서비스 배선
- `_calculate_entry_requirement_score(completed, department_id, admission_year)` → `_get_entry_requirement_groups` 호출 후 `scoring.entry_requirement_score_by_rules` 위임.
- **표시 연속성**: analysis_json 진입요건 상세와 `get_curriculum_details`의 "전공진입" 마킹이 쓰는 "필수과목 코드 목록"은 그룹 후보의 **합집합**으로 유지(마킹 대상 과목 집합은 동일하게 노출).

## 6. 데이터 흐름

```
evaluate_student(admission_year)
  └ _get_student_completed_courses  → details[*].numeric_grade
  └ _calculate_entry_requirement_score(department_id, admission_year)
       └ _get_entry_requirement_groups(dept, year)  → groups(target_min/required_count/candidates)
       └ scoring.entry_requirement_score_by_rules(groups, completed)  → 0~100 (부분·OR-max)
  └ overall = entry*0.4 + recommended_similar*0.3 + curriculum_similar*0.3
```

## 7. 테스트 전략

### 7.1 순수 단위 (빠름, DB 무관)
- 그룹 충족: 자격과목수 == required_count → 100.
- 미충족: 자격과목수 < required_count → 부분(예: 1/2 → 50).
- OR 최댓값: group1(A·1) 미충족 + group2(B·2) 부분 → 더 큰 쪽.
- 성적 경계: target A(4.0)에서 A0=4.0 통과, B+=3.3 실패; target B(3.0)에서 B0=3.0 통과.
- numeric_grade 폴백: numeric 없음 → GRADE_TO_NUMERIC.
- 요건 없음 → 100.0.

### 7.2 SQLite 통합 (실 동작)
- ELEC 2026 형태(2그룹) 시드: (A 1과목) OR (B 2과목).
  - A+ 1과목만 이수 → group1 충족 → 100.
  - B0 2과목 이수 → group2 충족 → 100.
  - B0 1과목만 → group2 50%, group1 0% → 50.

### 7.3 회귀
- 기존 `test_evaluate_student_success`(=`_get_department_courses` mock 기반)와 characterization은 mock으로 진입요건을 우회하므로 대부분 유지.
- **갱신 대상(의도된 변경)**: `backend/tests/unit/test_scoring_unit.py`의 진입요건 3개(`test_entry_no_requirement_is_100`, `test_entry_partial_ratio_is_rounded`, `test_entry_name_match_also_counts`)는 옛 "개수 비율" 함수를 고정한다. 규칙 기반 함수로 교체되므로 신규 규칙 단위 테스트(7.1)로 대체한다. "요건 없음 → 100" 케이스는 유지.

## 8. 범위 밖 (Out of scope)

- `logic_operator`(AND/OR) 그룹 결합: 이번엔 전 그룹 OR 고정. 향후 서로 다른 요건 블록 간 AND가 필요해지면 별도 작업.
- `is_alert_required` 알림 UI 노출.
- 유사과목 대체를 진입요건에 도입.
- DB 컬럼 리네이밍/마이그레이션.

## 9. 완료 기준 (Acceptance)

- 진입요건 점수가 4개 규칙(성적기준·필요개수·그룹 OR·부분점수)을 반영한다.
- 7.1/7.2 신규 테스트 통과, 전체 스위트 green.
- `logic_operator` 미사용을 코드/주석에 명시(오해 방지).
