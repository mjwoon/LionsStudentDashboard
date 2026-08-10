"""
graphDB 전용 Neo4j 연결 헬퍼.

graphDB 는 ADR 0001에 따라 lions-core workspace 멤버가 아니므로 lions_core.graph_service
를 import 할 수 없다. 따라서 자체 연결 헬퍼를 유지하되, 드라이버 생성을 한 곳으로 모으고
컨텍스트 매니저를 제공해 재사용성과 테스트 용이성을 확보한다.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from neo4j import Driver, GraphDatabase

from config import Settings


def create_driver(uri: str, user: str, password: str) -> Driver:
    """Neo4j 드라이버 생성(단일 진입점)."""
    return GraphDatabase.driver(uri, auth=(user, password))


def driver_from_settings(settings: Settings) -> Driver:
    """Settings 로부터 드라이버 생성."""
    return create_driver(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


@contextmanager
def connected_driver(settings: Settings) -> Iterator[Driver]:
    """with 블록 종료 시 드라이버를 자동으로 닫는 컨텍스트 매니저."""
    driver = driver_from_settings(settings)
    try:
        yield driver
    finally:
        driver.close()
