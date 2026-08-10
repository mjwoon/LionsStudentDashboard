"""하위호환 shim — graph_service는 인프라/도메인 두 모듈로 분리되었다.

- 인프라(연결·세션·health): lions_core.graph_connection
- 도메인 질의(Cypher):      lions_core.course_graph_service

기존 import 경로(`from lions_core.graph_service import ...`,
`from services.graph_service import ...`)를 깨지 않기 위해 재노출한다.
"""
from lions_core.graph_connection import (  # noqa: F401
    Neo4jConnection,
    get_neo4j_driver,
    get_session,
    is_graph_available,
)
from lions_core.course_graph_service import CourseGraphService  # noqa: F401
