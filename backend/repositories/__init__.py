"""
영속성 경계 — 리포지토리 계층.

하이브리드 전략: 평가/캐시처럼 테스트가 중요하고 접근이 반복되는 애그리거트만
리포지토리로 감싸 ORM 접근을 격리한다. 단순 1회성 조회는 서비스/라우터에 남겨둔다.
"""

from repositories.evaluation_repository import (
    DepartmentRepository,
    EvaluationCacheRepository,
    StudentRepository,
)

__all__ = [
    "StudentRepository",
    "DepartmentRepository",
    "EvaluationCacheRepository",
]
