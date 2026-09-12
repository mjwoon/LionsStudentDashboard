"""진입요건 게이트 — 요건은 가중치가 아니라 관문이다.

배경: overall_score는 0.4*진입요건 + 0.3*권장 + 0.3*교육과정 가중합이라
  요건 완전 미충족 (0, 100, 100) -> 60점 (D)
  요건 완전 충족   (100, 0,  0)  -> 40점 (F)
처럼 관문을 못 넘은 학생이 넘은 학생보다 높은 등급을 받는 역전이 생긴다.
임계값을 어디로 옮겨도 이 역전은 사라지지 않는다 — 성질이 다른 두 질문
('진입할 수 있나' / '얼마나 준비됐나')을 한 숫자로 뭉갠 탓이다.

점수 자체는 그대로 두고(정보 손실 없음), 등급과 순위를 게이트가 지배하게 한다.
"""

from lions_core import scoring


def test_gate_open_when_requirement_satisfied():
    breakdown = {"score": 100.0, "satisfied": True, "has_requirement": True}
    assert scoring.entry_gate_state(breakdown) == "open"


def test_gate_blocked_when_requirement_not_satisfied():
    breakdown = {"score": 40.0, "satisfied": False, "has_requirement": True}
    assert scoring.entry_gate_state(breakdown) == "blocked"


def test_gate_unknown_when_no_requirement_registered():
    """요건이 등록되지 않은 학과는 '통과'도 '미통과'도 아니다 — 알 수 없다."""
    breakdown = {"score": 100.0, "satisfied": True, "has_requirement": False}
    assert scoring.entry_gate_state(breakdown) == "unknown"


def test_grade_withheld_when_gate_blocked():
    """관문을 못 넘었으면 등급을 부여하지 않는다. 준비도 점수는 그대로 남는다."""
    assert scoring.grade_for("blocked", 60.0) is None


def test_grade_given_when_gate_open():
    assert scoring.grade_for("open", 85.0) == "B"


def test_grade_given_when_gate_unknown():
    """요건을 모르는 학과까지 등급을 막으면 대부분의 학과가 빈칸이 된다.
    알 수 없음은 미충족과 다르므로 준비도 등급은 그대로 준다."""
    assert scoring.grade_for("unknown", 85.0) == "B"


def test_no_inversion_between_blocked_and_open():
    """역전 재현 케이스: 미충족 60점이 충족 40점을 이기지 못해야 한다."""
    blocked = scoring.ranking_key("blocked", 60.0)
    opened = scoring.ranking_key("open", 40.0)
    assert opened > blocked


def test_ranking_prefers_higher_score_within_same_gate():
    assert scoring.ranking_key("open", 70.0) > scoring.ranking_key("open", 40.0)


def test_ranking_places_unknown_between_open_and_blocked():
    """요건 미등록(unknown)은 확인된 미충족보다는 앞, 확인된 충족보다는 뒤."""
    assert (
        scoring.ranking_key("open", 10.0)
        > scoring.ranking_key("unknown", 90.0)
        > scoring.ranking_key("blocked", 90.0)
    )


# ---------------------------------------------------------------------------
# pending — '아직 안 들음'과 '들었는데 성적 미달'은 다르다
#
# 이 시스템의 대상은 자율전공학부 1학년이고 2학년 진입을 준비하는 단계다.
# 요건 과목을 아직 안 들은 것은 정상 상태이지 차단 사유가 아니다. qualifying만
# 세면 미이수 학생과 성적 미달 학생이 똑같이 0으로 떨어져 둘 다 blocked이 된다.
# ---------------------------------------------------------------------------

def _completed_with(details):
    return {
        "codes": {d["course_code"] for d in details},
        "names": {d["course_name"] for d in details},
        "details": details,
    }


def _course_detail(code, name, numeric):
    return {"course_code": code, "course_name": name, "grade": "", "credits": 3,
            "numeric_grade": numeric}


def _group(codes, required=1, target_min=3.0):
    return {"group": 1, "target_min": target_min, "required_count": required,
            "candidate_codes": set(codes)}


def test_breakdown_reports_attempted_regardless_of_grade():
    """성적이 모자라도 '이수 시도'로는 잡힌다."""
    completed = _completed_with([_course_detail("AAA1001", "과목A", 1.0)])
    b = scoring.entry_requirement_breakdown([_group(["AAA1001"])], completed)

    assert b["attempted"] == 1
    assert b["qualifying"] == 0


def test_breakdown_attempted_zero_when_never_taken():
    completed = _completed_with([_course_detail("ZZZ9999", "다른과목", 4.5)])
    b = scoring.entry_requirement_breakdown([_group(["AAA1001"])], completed)

    assert b["attempted"] == 0
    assert b["qualifying"] == 0


def test_gate_pending_when_requirement_courses_not_taken_yet():
    """미이수는 차단이 아니라 진행 전이다."""
    breakdown = {"score": 0.0, "satisfied": False, "has_requirement": True,
                 "required": 1, "attempted": 0}
    assert scoring.entry_gate_state(breakdown) == "pending"


def test_gate_blocked_only_when_attempted_but_short():
    """들었는데 성적이 모자란 경우만 진짜 차단이다."""
    breakdown = {"score": 0.0, "satisfied": False, "has_requirement": True,
                 "required": 1, "attempted": 1}
    assert scoring.entry_gate_state(breakdown) == "blocked"


def test_grade_given_when_pending():
    """미이수 학생에게까지 등급을 지우면 1학년 대부분이 빈칸이 된다."""
    assert scoring.grade_for("pending", 55.0) == "F"


def test_ranking_order_open_pending_unknown_blocked():
    """요건 충족 > 미이수 > 요건 미등록 > 성적 미달."""
    assert (
        scoring.ranking_key("open", 10.0)
        > scoring.ranking_key("pending", 90.0)
        > scoring.ranking_key("unknown", 90.0)
        > scoring.ranking_key("blocked", 90.0)
    )
