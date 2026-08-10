"""하위호환 shim — analysis_json 빌더는 lions_core.evaluation_presenter로 이동.

analysis_json은 StudentRequirementStatus.analysis_json으로 영속화되는 도메인 데이터이며
빌더는 ORM 모델에만 의존하는 순수 로직이므로 공유 코어(lions-core)로 이동했다.
이 이동으로 lions-core → backend 역참조(순환 의존)가 제거되었다.
"""
from lions_core.evaluation_presenter import EvaluationResponseBuilder  # noqa: F401
