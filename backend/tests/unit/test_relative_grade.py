"""상대 적합도 등급 — 순위 밴드와 절대 상한의 상호작용.

절대 경계로는 A가 한 건도 나오지 않았다(실측 9,900건 중 0건, F 97.4%). 학생 한 명을
38개 학과에 대해 평가하니 대부분 조합이 안 맞는 것이 정상이기 때문이다. 등급을
"이 학생의 선택지 중 어디쯤"으로 바꾸되, 순위만으로 주면 어느 학과와도 겹치는 과목이
없는 학생에게도 A가 붙으므로 절대 준비도로 상한을 건다.
"""
from lions_core import scoring


def test_top_rank_with_solid_score_gets_a():
    assert scoring.relative_grade(scoring.GATE_OPEN, 50.0, 1, 38) == "A"


def test_bottom_rank_cannot_ride_a_high_score():
    """순위가 낮으면 점수가 높아도 상위 등급을 주지 않는다."""
    assert scoring.relative_grade(scoring.GATE_OPEN, 50.0, 30, 38) == "F"


def test_top_rank_is_capped_by_weak_absolute_score():
    """1등이어도 준비도가 5점이면 A가 될 수 없다 — 모든 학생이 A를 갖는 것을 막는다."""
    assert scoring.relative_grade(scoring.GATE_OPEN, 5.0, 1, 38) == "D"


def test_zero_score_is_f_even_at_top():
    assert scoring.relative_grade(scoring.GATE_OPEN, 0.0, 1, 38) == "F"


def test_blocked_gate_keeps_withholding_grade():
    assert scoring.relative_grade(scoring.GATE_BLOCKED, 50.0, 1, 38) is None


def test_pending_and_unknown_still_graded():
    assert scoring.relative_grade(scoring.GATE_PENDING, 50.0, 1, 38) == "A"
    assert scoring.relative_grade(scoring.GATE_UNKNOWN, 50.0, 1, 38) == "A"


def test_missing_score_has_no_grade():
    assert scoring.relative_grade(scoring.GATE_OPEN, None, 1, 38) is None


def test_falls_back_to_absolute_without_rank_context():
    """순위 정보가 없으면 절대 경계로 돌아간다.

    한 학과만 평가된 상태에서 그 학과가 자동으로 1등이 되어 A를 받는 일을 막는다.
    """
    assert scoring.relative_grade(scoring.GATE_OPEN, 95.0, None, None) == "A"
    assert scoring.relative_grade(scoring.GATE_OPEN, 50.0, None, None) == "F"
    assert scoring.relative_grade(scoring.GATE_OPEN, 50.0, 1, 1) == "F"


def test_band_boundaries_on_38_departments():
    g = lambda r: scoring._band_grade(r, 38)
    assert (g(1), g(3), g(4), g(9), g(10), g(19), g(20), g(28), g(29)) == (
        "A", "A", "B", "B", "C", "C", "D", "D", "F"
    )
