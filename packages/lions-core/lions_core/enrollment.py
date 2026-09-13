"""수강 한 건의 이수 상태 — 점수·표·학점 집계가 같은 기준을 쓰게 하는 한 곳.

왜 여기 모으는가
---------------
같은 판정이 저장소 안에 세 벌 있었고 서로 달랐다.

    evaluation_service._completion_status   성적 없음 -> in_progress, F -> failed
    student_service.calculate_...           성적 없음·F 제외 (인라인 필터)
    routers/students.get_student_courses    아무 필터도 없음  <- 버그

세 번째 때문에 학생 화면의 '총 취득학점'이 수강중 과목까지 더하고 있었다
(예: 2026665579 = 취득 16 + 수강중 12 = 28로 표시). 라벨은 '취득학점'인데
집계는 '수강학점'이었다.

기준이 갈리면 표에는 이수로 뜨는 과목이 점수에는 안 잡히는 일이 생긴다.
_completion_status의 원래 docstring이 지적한 그대로이며, 그 함수가 이 모듈을 쓴다.
"""
from __future__ import annotations

from typing import Iterable

from .constants import FAILING_GRADE

COMPLETED = "completed"      # 성적이 나왔고 낙제가 아니다
FAILED = "failed"            # F — 이수가 아니다
IN_PROGRESS = "in_progress"  # 수강했지만 성적이 아직 없다(진행 중인 학기)
NOT_TAKEN = "not_taken"      # 수강 이력이 없다


def completion_status(enrollment) -> str:
    """수강 한 건의 이수 상태.

    enrollment는 .grade 속성을 가진 무엇이든 된다(ORM 객체, 네임스페이스 등).
    None이면 '수강 이력 없음'으로 본다 — 교육과정 표가 미수강 칸을 그릴 때 쓴다.
    """
    if enrollment is None:
        return NOT_TAKEN
    if not enrollment.grade:
        return IN_PROGRESS
    if enrollment.grade == FAILING_GRADE:
        return FAILED
    return COMPLETED


def is_earned(enrollment) -> bool:
    """학점으로 인정되는 수강인가 — 성적이 확정됐고 F가 아니어야 한다.

    수강중(성적 미부여)은 아직 학점이 아니다. 이번 학기가 끝나야 정해진다.
    """
    return completion_status(enrollment) == COMPLETED


def earned_credits(enrollments: Iterable) -> int:
    """취득학점 합계.

    학점은 수강 이력 자체(StudentCourse.credits)에서 가져온다. 과목 마스터가 아니다 —
    마스터의 학점은 공란이거나 수강 이력과 다른 경우가 있고(현 데이터 3,386행 중 549행),
    무엇보다 화면의 수강 과목 표가 보여주는 값이 수강 이력 쪽이다. 합계가 표의 행들과
    맞지 않으면 숫자를 믿을 수 없게 된다.
    """
    return sum(e.credits for e in enrollments if is_earned(e))
