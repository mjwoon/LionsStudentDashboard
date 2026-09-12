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
