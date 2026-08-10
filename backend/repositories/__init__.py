"""하위호환 shim — 리포지토리는 lions_core.repositories로 이동."""
from lions_core.repositories import (  # noqa: F401
    StudentRepository, DepartmentRepository, EvaluationCacheRepository,
)
