"""
Neo4j 영속성/조회 레이어.

  - GraphWriter : 노드·엣지·인덱스 쓰기 (build 파이프라인 전용)
  - GraphReader : 런타임 조회 (통계, 유사 과목 검색)

중요 — 여기서 만드는 그래프 스키마(라벨/프로퍼티/관계 타입)는 backend
(lions_core.graph_service)가 읽는 **동결 계약**이다. 이름을 바꾸면 backend 가 깨진다:
  노드 :Course {id, code, name, credits, category, department,
                description, summary, unmapped_prerequisites}
  관계 SIMILAR_TO {similarity} / IDENTICAL_ID {dept1, dept2} / REQUIRES {similarity, raw_text}
"""

from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd
from neo4j import Driver

from similarity_engine import IdenticalIdEdge, PrereqEdge, SimilarityEdge

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


class GraphWriter:
    """CSV/계산 결과를 Neo4j 그래프로 영속화."""

    def __init__(self, driver: Driver):
        self.driver = driver

    def clear_database(self) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("기존 데이터베이스 초기화 완료")

    def create_indexes(self) -> None:
        with self.driver.session() as session:
            session.run("CREATE INDEX course_id IF NOT EXISTS FOR (c:Course) ON (c.id)")
            session.run("CREATE INDEX course_code IF NOT EXISTS FOR (c:Course) ON (c.code)")
            session.run("CREATE INDEX course_name IF NOT EXISTS FOR (c:Course) ON (c.name)")
        logger.info("인덱스 생성 완료")

    def create_graph(
        self,
        df: pd.DataFrame,
        edges: List[SimilarityEdge],
        identical_edges: List[IdenticalIdEdge] | None = None,
        prereq_edges: List[PrereqEdge] | None = None,
        unmapped_prereqs: Dict[int, List[str]] | None = None,
    ) -> None:
        """노드 + 3종 엣지(SIMILAR_TO / IDENTICAL_ID / REQUIRES)를 생성."""
        unmapped_prereqs = unmapped_prereqs or {}
        logger.info("그래프 생성 중...")

        with self.driver.session() as session:
            self._create_nodes(session, df, unmapped_prereqs)

            self._write_edges(
                session, "유사도",
                [{"source": e[0], "target": e[1], "weight": e[2]} for e in edges],
                """
                UNWIND $edges AS edge
                MATCH (c1:Course {id: edge.source})
                MATCH (c2:Course {id: edge.target})
                CREATE (c1)-[:SIMILAR_TO {similarity: edge.weight}]->(c2)
                """,
            )

            if identical_edges:
                self._write_edges(
                    session, "동일 학수번호",
                    [{"source": e[0], "target": e[1], "dept1": e[2], "dept2": e[3]}
                     for e in identical_edges],
                    """
                    UNWIND $edges AS edge
                    MATCH (c1:Course {id: edge.source})
                    MATCH (c2:Course {id: edge.target})
                    CREATE (c1)-[:IDENTICAL_ID {
                        dept1: edge.dept1,
                        dept2: edge.dept2,
                        note: '동일 학수번호, 다른 설강학과'
                    }]->(c2)
                    """,
                )

            if prereq_edges:
                self._write_edges(
                    session, "선수강",
                    [{"source": e[0], "target": e[1], "weight": e[2], "raw_text": e[3]}
                     for e in prereq_edges],
                    """
                    UNWIND $edges AS edge
                    MATCH (c1:Course {id: edge.source})
                    MATCH (c2:Course {id: edge.target})
                    CREATE (c1)-[:REQUIRES {
                        similarity: edge.weight,
                        raw_text: edge.raw_text,
                        note: '선수강과목 매핑'
                    }]->(c2)
                    """,
                )

        logger.info("그래프 생성 완료")

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────
    def _create_nodes(
        self, session, df: pd.DataFrame, unmapped_prereqs: Dict[int, List[str]]
    ) -> None:
        logger.info("  - 노드 생성 중...")
        has_credits = "학점" in df.columns
        has_grade = "학년" in df.columns

        for idx, row in df.iterrows():
            # NOTE(레거시 보존): 학점이 없을 때 '학년'을 credits 로 대체하는 기존 동작을
            # 그대로 둔다. 이 값은 backend(c.credits)가 소비하므로 데이터 계약에 영향이 있어
            # 별도 결정 전까지 변경하지 않는다.
            credits = 0
            if has_credits and pd.notna(row.get("학점")):
                credits = int(row["학점"])
            elif has_grade and pd.notna(row.get("학년")):
                credits = int(row["학년"])

            session.run(
                """
                CREATE (c:Course {
                    id: $id,
                    code: $code,
                    name: $name,
                    credits: $credits,
                    category: $category,
                    department: $department,
                    description: $description,
                    summary: $summary,
                    unmapped_prerequisites: $unmapped_reqs
                })
                """,
                id=int(idx),
                code=row.get("학수번호", ""),
                name=row["교과목 이름"],
                credits=credits,
                category=row["이수구분"] if pd.notna(row["이수구분"]) else "",
                department=row["설강학과"] if pd.notna(row["설강학과"]) else "",
                description=row["교과목개요"] if pd.notna(row["교과목개요"]) else "",
                summary=(row.get("교과목개요_요약", "")
                         if pd.notna(row.get("교과목개요_요약")) else ""),
                unmapped_reqs=", ".join(unmapped_prereqs.get(idx, [])),
            )

    @staticmethod
    def _write_edges(session, label: str, rows: List[dict], cypher: str) -> None:
        """엣지 dict 리스트를 배치 UNWIND 로 기록(3종 관계 공용)."""
        total = len(rows)
        if not total:
            return
        logger.info("  - %s 엣지 생성 중...", label)
        for i in range(0, total, _BATCH_SIZE):
            session.run(cypher, edges=rows[i:i + _BATCH_SIZE])
            logger.info("    진행: %d/%d", min(i + _BATCH_SIZE, total), total)


class GraphReader:
    """런타임 조회 (통계, 유사 과목 검색)."""

    def __init__(self, driver: Driver):
        self.driver = driver

    def get_statistics(self) -> dict:
        with self.driver.session() as session:
            stats = session.run(
                """
                MATCH (c:Course)
                OPTIONAL MATCH (c)-[r:SIMILAR_TO]-()
                RETURN
                    count(DISTINCT c) as num_courses,
                    count(r) as num_edges,
                    avg(r.similarity) as avg_similarity,
                    max(r.similarity) as max_similarity,
                    min(r.similarity) as min_similarity
                """
            ).single()
            req = session.run(
                "MATCH ()-[r:REQUIRES]->() RETURN count(r) as num_requires"
            ).single()

        return {
            "num_courses": stats["num_courses"],
            "num_edges": stats["num_edges"] // 2 if stats["num_edges"] else 0,
            "num_requires": req["num_requires"],
            "avg_similarity": stats["avg_similarity"] or 0.0,
            "max_similarity": stats["max_similarity"] or 0.0,
            "min_similarity": stats["min_similarity"] or 0.0,
        }

    def find_similar_courses(self, course_name: str, top_k: int = 10) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c1:Course {name: $name})-[r:SIMILAR_TO]-(c2:Course)
                RETURN c2.name as name,
                       c2.code as code,
                       c2.summary as summary,
                       r.similarity as similarity
                ORDER BY r.similarity DESC
                LIMIT $top_k
                """,
                name=course_name,
                top_k=top_k,
            )
            return [dict(record) for record in result]
