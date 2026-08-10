"""
Neo4j 그래프 통합 테스트.

구축된 그래프가 실제로 존재할 때만 검증하고, DB 연결이 안 되면 전체를 자동 skip 한다.
기존 test_queries.py(애드혹 육안 확인 스크립트)를 정식 테스트로 승격한 것이다.
raw Cypher 대신 GraphReader / CourseGraphValidator 를 재사용한다.

실행: (Neo4j 기동 상태에서) uv run python -m unittest tests.test_graph_integration
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Settings  # noqa: E402
from course_graph_analysis import (  # noqa: E402
    CourseGraphValidator,
    collect_validation_report,
    format_validation_report,
)
from graph_repository import GraphReader  # noqa: E402
from neo4j_client import create_driver  # noqa: E402


def _try_connect():
    """Settings(env) 우선, 실패 시 알려진 개발 비밀번호로 폴백해 드라이버 반환."""
    settings = Settings.from_env()
    for pw in [settings.neo4j_password, "password123", "your_password", "password"]:
        driver = None
        try:
            driver = create_driver(settings.neo4j_uri, settings.neo4j_user, pw)
            driver.verify_connectivity()
            return driver
        except Exception:
            if driver is not None:
                driver.close()  # 실패한 드라이버는 닫아 리소스 누수 방지
            continue
    return None


class GraphIntegrationTest(unittest.TestCase):
    driver = None

    @classmethod
    def setUpClass(cls):
        cls.driver = _try_connect()
        if cls.driver is None:
            raise unittest.SkipTest("Neo4j 연결 불가 — 그래프 통합 테스트를 skip 합니다.")

    @classmethod
    def tearDownClass(cls):
        if cls.driver is not None:
            cls.driver.close()

    def test_courses_exist(self):
        stats = GraphReader(self.driver).get_statistics()
        self.assertGreater(stats["num_courses"], 0)

    def test_requires_edges_have_raw_text(self):
        # REQUIRES 엣지가 있다면 모두 raw_text 원문을 보존해야 한다.
        with self.driver.session() as s:
            rows = list(s.run(
                "MATCH ()-[r:REQUIRES]->() RETURN r.raw_text AS raw_text LIMIT 50"
            ))
        for row in rows:
            self.assertIsNotNone(row["raw_text"])

    def test_validation_report_renders(self):
        validator = CourseGraphValidator(driver=self.driver)
        report = collect_validation_report(validator)
        self.assertIn("summary", report)
        self.assertIn("node", report["summary"])
        # 수집한 구조화 리포트가 포매터로 렌더 가능해야 한다.
        self.assertIsInstance(format_validation_report(report), str)

    def test_unmapped_prerequisites_shape(self):
        validator = CourseGraphValidator(driver=self.driver)
        for item in validator.get_unmapped_prerequisites(limit=5):
            self.assertIn("course_name", item)
            self.assertIn("unmapped_text", item)


if __name__ == "__main__":
    unittest.main()
