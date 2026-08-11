# Entry Requirement Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make entry-requirement scoring honor `DepartmentEntryRequirement` rule fields (target_grade_level, required_count, all-groups-OR) with a partial (0–100) score.

**Architecture:** Add a pure scoring function in `lions_core/scoring.py`; feed it group rules fetched via a new service method and completed courses enriched with numeric grades. Keep display paths (analysis_json, curriculum_details) on the existing course-list fetch. Behavior-changing (score formula changes), so it lands on the dedicated branch with tests updated as intended changes.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, pytest (run from `backend/` via `uv run pytest`). lions-core is a uv workspace package consumed by backend.

## Global Constraints

- Run all tests from `backend/`: `uv run pytest`.
- Grade minimums (SSOT): `constants.GRADE_LEVEL_MINIMUM` — A→4.0, B→3.0, C→2.0, D→1.0, F→0.0.
- Weights SSOT: `constants.EVALUATION_WEIGHTS` (entry_requirement 0.4). Do not change weight values.
- `logic_operator` and `is_alert_required` are OUT OF SCOPE — all groups combine as OR.
- Entry-requirement matching is by `course_code` only; no similar-course (Neo4j) substitution.
- Pure functions in `scoring.py` must not import Session/Neo4j.
- Spec: `docs/superpowers/specs/2026-08-11-entry-requirement-rules-design.md`.

---

### Task 1: Pure rule-based scoring function

**Files:**
- Modify: `packages/lions-core/lions_core/scoring.py`
- Test: `backend/tests/unit/test_scoring_unit.py`

**Interfaces:**
- Produces: `entry_requirement_score_by_rules(groups: List[Dict], student_completed_courses: Dict) -> float`
  - `groups`: `[{"group": int, "target_min": float, "required_count": int, "candidate_codes": Set[str]}]`
  - `student_completed_courses`: `{"codes": Set[str], "names": Set[str], "details": [{"course_code": str, "course_name": str, "grade": str, "credits": int, "numeric_grade": float}]}`
  - Returns 0.0–100.0. Empty `groups` → 100.0.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/unit/test_scoring_unit.py`:

```python
def _course_detail(code, name, numeric):
    return {"course_code": code, "course_name": name, "grade": "", "credits": 3, "numeric_grade": numeric}


def test_rules_no_groups_is_100():
    assert scoring.entry_requirement_score_by_rules([], _completed([])) == 100.0


def test_rules_group_satisfied_is_100():
    groups = [{"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"A1", "A2"}}]
    completed = _completed([_course_detail("A1", "x", 4.0)])
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 100.0


def test_rules_group_partial_progress():
    groups = [{"group": 1, "target_min": 3.0, "required_count": 2, "candidate_codes": {"B1", "B2", "B3"}}]
    completed = _completed([_course_detail("B1", "x", 3.0)])  # 1 of 2 qualifying
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 50.0


def test_rules_all_groups_or_takes_max():
    groups = [
        {"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"C1"}},        # need A: 0%
        {"group": 2, "target_min": 3.0, "required_count": 2, "candidate_codes": {"C1", "C2"}},  # have 1/2: 50%
    ]
    completed = _completed([_course_detail("C1", "x", 3.0)])
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 50.0


def test_rules_grade_below_target_excluded():
    groups = [{"group": 1, "target_min": 4.0, "required_count": 1, "candidate_codes": {"D1"}}]
    completed = _completed([_course_detail("D1", "x", 3.3)])  # B+ < 4.0
    assert scoring.entry_requirement_score_by_rules(groups, completed) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_scoring_unit.py -q`
Expected: FAIL with `AttributeError: module 'lions_core.scoring' has no attribute 'entry_requirement_score_by_rules'`

- [ ] **Step 3: Implement the function**

Append to `packages/lions-core/lions_core/scoring.py`:

```python
def entry_requirement_score_by_rules(
    groups: List[Dict],
    student_completed_courses: Dict,
) -> float:
    """진입요건 부분 점수 (0~100).

    각 그룹: 후보과목 중 numeric_grade >= target_min 인 이수과목 수가
    required_count 이상이면 100%, 아니면 min(자격수/required_count, 1)*100.
    모든 그룹은 OR 관계이므로 그룹 진행률의 최댓값을 반환한다.
    요건 그룹이 없으면 100.0.
    """
    if not groups:
        return 100.0

    completed_numeric = {
        d["course_code"]: (d.get("numeric_grade") or 0.0)
        for d in student_completed_courses["details"]
    }

    best = 0.0
    for group in groups:
        target_min = group["target_min"]
        required = group["required_count"]
        qualifying = sum(
            1
            for code in group["candidate_codes"]
            if completed_numeric.get(code, 0.0) >= target_min
        )
        progress = 100.0 if required <= 0 else min(qualifying / required, 1.0) * 100
        if progress > best:
            best = progress

    return round(best, 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_scoring_unit.py -q`
Expected: PASS (all, including the 5 new ones)

- [ ] **Step 5: Commit**

```bash
git add packages/lions-core/lions_core/scoring.py backend/tests/unit/test_scoring_unit.py
git commit -m "feat(lions-core): add rule-based entry requirement scoring (pure)"
```

---

### Task 2: Enrich completed-course details with numeric_grade

**Files:**
- Modify: `packages/lions-core/lions_core/evaluation_service.py` (constants import; `_get_student_completed_courses`)
- Test: `backend/tests/services/test_completed_numeric_grade.py` (create)

**Interfaces:**
- Consumes: `constants.GRADE_TO_NUMERIC`.
- Produces: `_get_student_completed_courses(enrollments)` details now include key `"numeric_grade": float` (from `StudentCourse.numeric_grade`, else `GRADE_TO_NUMERIC[grade]`, else 0.0).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services/test_completed_numeric_grade.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import Base, Course, StudentCourse
from services.evaluation_service import EvaluationService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def test_completed_details_include_numeric_grade(session):
    session.add(Course(course_code="X", course_name="xx", credits=3, course_year=1, semester=1))
    session.add(Course(course_code="Y", course_name="yy", credits=3, course_year=1, semester=1))
    session.commit()
    svc = EvaluationService(db=session)

    enrollments = [
        StudentCourse(student_id=1, course_code="X", grade="A+", numeric_grade=4.5, year=2026, semester=1),
        StudentCourse(student_id=1, course_code="Y", grade="B", numeric_grade=None, year=2026, semester=1),
    ]
    details = {d["course_code"]: d for d in svc._get_student_completed_courses(enrollments)["details"]}

    assert details["X"]["numeric_grade"] == 4.5           # from StudentCourse.numeric_grade
    assert details["Y"]["numeric_grade"] == 3.0           # fallback GRADE_TO_NUMERIC["B"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/services/test_completed_numeric_grade.py -q`
Expected: FAIL with `KeyError: 'numeric_grade'`

- [ ] **Step 3: Re-add GRADE_TO_NUMERIC import**

In `packages/lions-core/lions_core/evaluation_service.py`, update the constants import block to include `GRADE_TO_NUMERIC`:

```python
from lions_core.constants import (
    GRADE_TO_NUMERIC,
    classify_grade,
    FIRST_YEAR,
    FAILING_GRADE,
    EVALUATION_WEIGHTS,
    SIMILARITY_THRESHOLD,
)
```

- [ ] **Step 4: Add numeric_grade to details**

In `_get_student_completed_courses`, after the `grade_map` line, add a `numeric_map`, and add `numeric_grade` to each appended detail. The method region becomes:

```python
        # grade 역참조 맵
        grade_map = {e.course_code: e.grade for e in valid_enrollments}
        # numeric 성적 맵: StudentCourse.numeric_grade 우선, 없으면 GRADE_TO_NUMERIC 폴백
        numeric_map = {
            e.course_code: (
                float(e.numeric_grade)
                if e.numeric_grade is not None
                else GRADE_TO_NUMERIC.get(e.grade, 0.0)
            )
            for e in valid_enrollments
        }

        for code, course in course_map.items():
            completed_codes.add(course.course_code)
            completed_names.add(course.course_name)
            completed_details.append({
                "course_code": course.course_code,
                "course_name": course.course_name,
                "grade": grade_map.get(code, ""),
                "credits": course.credits,
                "numeric_grade": numeric_map.get(code, 0.0),
            })
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/services/test_completed_numeric_grade.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/lions-core/lions_core/evaluation_service.py backend/tests/services/test_completed_numeric_grade.py
git commit -m "feat(lions-core): include numeric_grade in completed course details"
```

---

### Task 3: Fetch entry-requirement groups

**Files:**
- Modify: `packages/lions-core/lions_core/evaluation_service.py` (constants import; add `_get_entry_requirement_groups`)
- Test: `backend/tests/services/test_entry_requirement_groups.py` (create)

**Interfaces:**
- Consumes: `constants.GRADE_LEVEL_MINIMUM`; models `DepartmentEntryRequirement`, `RequirementCourse` (via `req.requirement_courses` relationship).
- Produces: `_get_entry_requirement_groups(department_id: int, admission_year: Optional[int] = None) -> List[Dict]` where each dict is `{"group": int, "target_min": float, "required_count": int, "candidate_codes": Set[str]}`. `admission_year=None` → all years.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services/test_entry_requirement_groups.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import (
    Base, Department, Course,
    DepartmentEntryRequirement, RequirementCourse, GradeLevelEnum,
)
from services.evaluation_service import EvaluationService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _seed(s):
    s.add(Department(id=1, code="ELEC", name="전자공학부"))
    for code in ("ELE3037", "GEN2052"):
        s.add(Course(course_code=code, course_name=code, credits=3, course_year=1, semester=1))
    s.add(DepartmentEntryRequirement(
        id=1, department_id=1, admission_year=2026, requirement_group=1,
        target_grade_level=GradeLevelEnum.A, required_count=1, requirement_text="t",
    ))
    s.add(DepartmentEntryRequirement(
        id=2, department_id=1, admission_year=2026, requirement_group=2,
        target_grade_level=GradeLevelEnum.B, required_count=2, requirement_text="t",
    ))
    s.add(RequirementCourse(id=1, requirement_id=1, course_code="ELE3037"))
    s.add(RequirementCourse(id=2, requirement_id=2, course_code="ELE3037"))
    s.add(RequirementCourse(id=3, requirement_id=2, course_code="GEN2052"))
    s.commit()


def test_groups_expose_target_min_and_candidates(session):
    _seed(session)
    svc = EvaluationService(db=session)
    groups = {g["group"]: g for g in svc._get_entry_requirement_groups(1, admission_year=2026)}

    assert groups[1]["target_min"] == 4.0        # A
    assert groups[1]["required_count"] == 1
    assert groups[1]["candidate_codes"] == {"ELE3037"}
    assert groups[2]["target_min"] == 3.0        # B
    assert groups[2]["required_count"] == 2
    assert groups[2]["candidate_codes"] == {"ELE3037", "GEN2052"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/services/test_entry_requirement_groups.py -q`
Expected: FAIL with `AttributeError: 'EvaluationService' object has no attribute '_get_entry_requirement_groups'`

- [ ] **Step 3: Add GRADE_LEVEL_MINIMUM import + the method**

In `evaluation_service.py` add `GRADE_LEVEL_MINIMUM` to the constants import block (alongside `GRADE_TO_NUMERIC`, etc.), then add the method next to `_get_department_courses`:

```python
    def _get_entry_requirement_groups(
        self, department_id: int, admission_year: Optional[int] = None
    ) -> List[Dict]:
        """진입요건 그룹을 규칙 형태로 조회.

        각 그룹: {group, target_min, required_count, candidate_codes}.
        admission_year가 있으면 해당 입학년도 요건만(7a 연도 필터와 동일 규칙).
        """
        query = self.db.query(DepartmentEntryRequirement).filter(
            DepartmentEntryRequirement.department_id == department_id
        )
        if admission_year is not None:
            query = query.filter(
                DepartmentEntryRequirement.admission_year == admission_year
            )

        groups = []
        for req in query.all():
            groups.append({
                "group": req.requirement_group,
                "target_min": GRADE_LEVEL_MINIMUM.get(req.target_grade_level.value, 0.0),
                "required_count": req.required_count,
                "candidate_codes": {rc.course_code for rc in req.requirement_courses},
            })
        return groups
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/services/test_entry_requirement_groups.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/lions-core/lions_core/evaluation_service.py backend/tests/services/test_entry_requirement_groups.py
git commit -m "feat(lions-core): fetch entry requirement groups as rule structures"
```

---

### Task 4: Wire the rule score into the service; retire the old ratio function

**Files:**
- Modify: `packages/lions-core/lions_core/evaluation_service.py` (`_calculate_entry_requirement_score`)
- Modify: `packages/lions-core/lions_core/scoring.py` (remove old `entry_requirement_score`)
- Modify: `backend/tests/unit/test_scoring_unit.py` (delete 3 obsolete old-entry tests)
- Modify: `backend/tests/services/test_evaluation_service.py` (update behavior-changed assertion)
- Test: `backend/tests/services/test_entry_requirement_rules_e2e.py` (create)

**Interfaces:**
- Consumes: `_get_entry_requirement_groups` (Task 3), `scoring.entry_requirement_score_by_rules` (Task 1).
- Produces: `_calculate_entry_requirement_score(student_completed_courses, department_id, admission_year=None)` now returns the rule-based partial score.

- [ ] **Step 1: Write the failing end-to-end test**

Create `backend/tests/services/test_entry_requirement_rules_e2e.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lions_core.models import (
    Base, Department, Course,
    DepartmentEntryRequirement, RequirementCourse, GradeLevelEnum,
)
from services.evaluation_service import EvaluationService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _seed_elec(s):
    s.add(Department(id=1, code="ELEC", name="전자공학부"))
    for code in ("A_ONLY", "B1", "B2"):
        s.add(Course(course_code=code, course_name=code, credits=3, course_year=1, semester=1))
    # group1: A(4.0), 1 course among {A_ONLY}; group2: B(3.0), 2 courses among {B1,B2}
    s.add(DepartmentEntryRequirement(id=1, department_id=1, admission_year=2026,
          requirement_group=1, target_grade_level=GradeLevelEnum.A, required_count=1, requirement_text="t"))
    s.add(DepartmentEntryRequirement(id=2, department_id=1, admission_year=2026,
          requirement_group=2, target_grade_level=GradeLevelEnum.B, required_count=2, requirement_text="t"))
    s.add(RequirementCourse(id=1, requirement_id=1, course_code="A_ONLY"))
    s.add(RequirementCourse(id=2, requirement_id=2, course_code="B1"))
    s.add(RequirementCourse(id=3, requirement_id=2, course_code="B2"))
    s.commit()


def _completed(details):
    return {"codes": {d["course_code"] for d in details},
            "names": {d["course_name"] for d in details},
            "details": details}


def _d(code, numeric):
    return {"course_code": code, "course_name": code, "grade": "", "credits": 3, "numeric_grade": numeric}


def test_group1_satisfied_by_single_A(session):
    _seed_elec(session)
    svc = EvaluationService(db=session)
    completed = _completed([_d("A_ONLY", 4.0)])       # group1 satisfied
    assert svc._calculate_entry_requirement_score(completed, 1, 2026) == 100.0


def test_group2_partial_one_of_two_B(session):
    _seed_elec(session)
    svc = EvaluationService(db=session)
    completed = _completed([_d("B1", 3.0)])           # group1 0%, group2 50% -> OR max 50
    assert svc._calculate_entry_requirement_score(completed, 1, 2026) == 50.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/services/test_entry_requirement_rules_e2e.py -q`
Expected: FAIL — current `_calculate_entry_requirement_score` uses `_get_department_courses`/old ratio, so `test_group2_partial_one_of_two_B` returns 100.0 (old logic counts B1 as a completed necessary course) instead of 50.0.

- [ ] **Step 3: Rewire `_calculate_entry_requirement_score`**

Replace its body:

```python
    def _calculate_entry_requirement_score(
        self,
        student_completed_courses: Dict,
        department_id: str,
        admission_year: Optional[int] = None
    ) -> float:
        """
        진입요건 충족 점수 (규칙 기반, 부분 점수 0~100).

        그룹별: 후보 중 성적 >= target_grade_level 인 이수과목이 required_count 이상이면 100%,
        아니면 진행률. 모든 그룹 OR → 최댓값. 요건 없으면 100.
        """
        groups = self._get_entry_requirement_groups(department_id, admission_year)
        return scoring.entry_requirement_score_by_rules(groups, student_completed_courses)
```

- [ ] **Step 4: Remove the obsolete pure function**

Delete `entry_requirement_score` (the old count-ratio function) from `packages/lions-core/lions_core/scoring.py`. (Its only caller was `_calculate_entry_requirement_score`, now rewired.)

- [ ] **Step 5: Delete obsolete unit tests**

In `backend/tests/unit/test_scoring_unit.py`, delete the three tests that call the removed function: `test_entry_no_requirement_is_100`, `test_entry_partial_ratio_is_rounded`, `test_entry_name_match_also_counts`. (The rule-based coverage from Task 1 replaces them; "no requirement → 100" is covered by `test_rules_no_groups_is_100`.)

- [ ] **Step 6: Update the behavior-changed characterization test**

In `backend/tests/services/test_evaluation_service.py`, the `evaluation_service` fixture already stubs internal methods. Add a stub so entry score is deterministic under the new path, keeping the existing `overall_score == 55.0` assertion valid (entry 100 * 0.4 + 0 * 0.3 + 50 * 0.3 = 55.0). In the fixture, after the other mocks, add:

```python
    service._calculate_entry_requirement_score = MagicMock(return_value=100.0)
```

Place it in the `evaluation_service` fixture in that file (alongside the existing `_is_graph_available`/`_save_evaluation_result` mocks). This isolates the orchestration test from the entry-rule internals (which have dedicated tests).

- [ ] **Step 7: Run the full suite**

Run: `cd backend && uv run pytest -q`
Expected: PASS (all). Confirms new e2e tests pass, obsolete tests gone, and no regression.

- [ ] **Step 8: Commit**

```bash
git add packages/lions-core/lions_core/evaluation_service.py \
        packages/lions-core/lions_core/scoring.py \
        backend/tests/unit/test_scoring_unit.py \
        backend/tests/services/test_evaluation_service.py \
        backend/tests/services/test_entry_requirement_rules_e2e.py
git commit -m "feat(lions-core): evaluate entry requirements by group rules (partial, OR)"
```

---

## Self-Review

**Spec coverage:**
- §3 rule semantics → Task 1 (pure fn), Task 4 (wiring). ✓
- §4 grade comparison (numeric_grade priority, GRADE_TO_NUMERIC fallback, code match, no similar) → Task 2 + Task 1 logic. ✓
- §5.1 numeric_grade in details → Task 2. ✓
- §5.2 `_get_entry_requirement_groups` → Task 3. ✓
- §5.3 pure `entry_requirement_score_by_rules` + remove old → Task 1 + Task 4. ✓
- §5.4 wiring + display continuity → Task 4 (score path); display paths (`_get_department_courses` for analysis_json/curriculum) untouched, so union-of-candidates display preserved. ✓
- §7 tests (pure unit, SQLite integration, regression update) → Tasks 1–4. ✓
- §8 out of scope (logic_operator, is_alert_required) → not touched. ✓

**Placeholder scan:** none.

**Type consistency:** group dict shape `{group, target_min, required_count, candidate_codes}` identical across Tasks 1/3/4; `entry_requirement_score_by_rules(groups, completed)` signature consistent; `_get_entry_requirement_groups(department_id, admission_year=None)` consistent. ✓

**Note on admission_year flow:** `evaluate_student` already passes `admission_year` into `_calculate_entry_requirement_score` (Phase 7a), so the rule path is year-scoped end-to-end with no further wiring.
