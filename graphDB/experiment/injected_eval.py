"""유사도·임계값을 주입하고 Neo4j를 우회하는 EvaluationService (오프라인 재현).

루트 3.12 환경에서만 실제 사용된다(backend `services` + `lions_core` 필요).
"""
from __future__ import annotations

from services.evaluation_service import EvaluationService


class InjectedEvaluationService(EvaluationService):
    def __init__(self, db, similarity_fn, threshold: float):
        super().__init__(db)
        self._similarity_fn = similarity_fn
        self._similarity_threshold = threshold

    def _is_graph_available(self) -> bool:
        return True

    def _get_similarity_from_graph(self, source_course_code, target_course_code) -> float:
        return self._similarity_fn(source_course_code, target_course_code)
