"""
Neo4j 인프라 계층 — 드라이버 싱글톤, 세션 컨텍스트, 연결 가용성(health) 캐시.

그래프 도메인 질의(course_graph_service.CourseGraphService)와 분리된 순수 인프라 계층.
"""

import time
import logging
from typing import Dict
from neo4j import GraphDatabase
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Neo4j 데이터베이스 연결 관리 클래스"""
    
    _instance = None
    _driver = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_driver(cls):
        """싱글톤 드라이버 인스턴스 반환"""
        if cls._driver is None:
            from lions_core.config import settings
            cls._driver = GraphDatabase.driver(
                settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
            )
        return cls._driver
    
    @classmethod
    def close(cls):
        """드라이버 연결 종료"""
        if cls._driver:
            cls._driver.close()
            cls._driver = None


def get_neo4j_driver():
    """Neo4j 드라이버 의존성 주입용 함수"""
    return Neo4jConnection.get_driver()


@contextmanager
def get_session():
    """Neo4j 세션 컨텍스트 매니저"""
    driver = get_neo4j_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


# ==================== 모듈 레벨 연결 상태 캐시 ====================
# 인스턴스마다 연결 확인을 반복하지 않도록 30초 TTL로 모듈 단위에서 관리
# - 일시적 Neo4j 장애 복구 시 최대 30초 이내에 자동 정상화
# - 모든 요청 간 공유 (EvaluationService 인스턴스 재생성과 무관)
_HEALTH_TTL_SECONDS = 30.0
_health_cache: Dict = {"available": None, "checked_at": 0.0}


def is_graph_available() -> bool:
    """
    Neo4j 연결 가능 여부 확인 (30초 TTL 모듈 레벨 캐시)

    Returns:
        True: Neo4j 연결 정상
        False: 연결 불가 (최대 30초 후 재확인)
    """
    now = time.monotonic()
    if now - _health_cache["checked_at"] > _HEALTH_TTL_SECONDS:
        try:
            get_neo4j_driver().verify_connectivity()
            _health_cache["available"] = True
        except Exception as e:
            logger.warning(f"Neo4j connectivity verification failed: {e}")
            _health_cache["available"] = False
        _health_cache["checked_at"] = now
    return bool(_health_cache["available"])
