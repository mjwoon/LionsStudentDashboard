"""수강 이수 상태 판정 — 점수·표·학점 집계가 공유하는 한 기준.

이 판정이 갈리면 표에는 '이수'로 뜨는 과목이 점수에는 안 잡히거나, 학점 합계가
표의 행들과 맞지 않는다. 실제로 세 벌이 따로 있었고 학생 화면의 총 취득학점만
아무 필터 없이 전부 더하고 있었다.
"""

from types import SimpleNamespace

from lions_core.enrollment import (
    COMPLETED,
    FAILED,
    IN_PROGRESS,
    NOT_TAKEN,
    completion_status,
    earned_credits,
    is_earned,
)


def enrollment(grade, credits=3):
    return SimpleNamespace(grade=grade, credits=credits)


def test_status_of_graded_pass():
    assert completion_status(enrollment("A0")) == COMPLETED
    assert completion_status(enrollment("P")) == COMPLETED


def test_status_of_failing_grade():
    assert completion_status(enrollment("F")) == FAILED


def test_status_of_ungraded_is_in_progress():
    """성적이 아직 없는 수강 — None과 빈 문자열 둘 다 '듣는 중'이다."""
    assert completion_status(enrollment(None)) == IN_PROGRESS
    assert completion_status(enrollment("")) == IN_PROGRESS


def test_status_of_missing_enrollment():
    assert completion_status(None) == NOT_TAKEN


def test_only_completed_counts_as_earned():
    assert is_earned(enrollment("B+")) is True
    assert is_earned(enrollment("F")) is False
    assert is_earned(enrollment(None)) is False
    assert is_earned(None) is False


def test_earned_credits_sums_only_earned():
    rows = [
        enrollment("A0", 3),   # 취득
        enrollment("B0", 2),   # 취득
        enrollment("F", 3),    # 낙제
        enrollment(None, 3),   # 수강중
        enrollment("", 1),     # 수강중
    ]
    assert earned_credits(rows) == 5


def test_earned_credits_of_empty_history():
    assert earned_credits([]) == 0
