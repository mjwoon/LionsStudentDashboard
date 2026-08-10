"""
교과목 유사도 기반 그래프 네트워크 구축 (파사드).

이 파일은 quick_start.py 등 기존 진입점이 의존하는 공개 API(CourseGraphBuilder)를
유지하는 얇은 파사드다. 실제 책임은 아래 세 컴포넌트로 분리되어 있다:

  - similarity_engine.SimilarityEngine : 임베딩·유사도·선수강/동일학수 관계 '계산'
  - graph_repository.GraphWriter        : Neo4j '쓰기' (노드/엣지/인덱스)
  - graph_repository.GraphReader        : Neo4j '조회' (통계/검색)

이렇게 분리하면 계산 로직을 DB 없이 단위 테스트할 수 있고, 연결/조회를 재사용할 수 있다.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from config import Settings
from graph_repository import GraphReader, GraphWriter
from neo4j_client import create_driver
from similarity_engine import (
    IdenticalIdEdge,
    PrereqEdge,
    SimilarityEdge,
    SimilarityEngine,
    load_course_data,
)

logger = logging.getLogger(__name__)


class CourseGraphBuilder:
    """교과목 그래프 네트워크 구축 파사드 (계산 + 쓰기 + 조회 조합)."""

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        *,
        model=None,
        hybrid_weight: float = 0.7,
    ):
        self.driver = create_driver(neo4j_uri, neo4j_user, neo4j_password)
        self.engine = SimilarityEngine(hybrid_weight=hybrid_weight, model=model)
        self.writer = GraphWriter(self.driver)
        self.reader = GraphReader(self.driver)

    def close(self) -> None:
        self.driver.close()

    # ── 데이터/계산 (SimilarityEngine 위임) ───────────────────────────
    def load_course_data(self, csv_path: str) -> pd.DataFrame:
        return load_course_data(csv_path)

    def create_embeddings(self, df: pd.DataFrame, use_tfidf_weighting: bool = True) -> np.ndarray:
        return self.engine.create_embeddings(df, use_tfidf_weighting=use_tfidf_weighting)

    def compute_similarity(
        self, df: pd.DataFrame, embeddings: np.ndarray, threshold: float = 0.7
    ) -> List[SimilarityEdge]:
        return self.engine.compute_similarity(df, embeddings, threshold=threshold)

    def compute_identical_id_edges(self, df: pd.DataFrame) -> List[IdenticalIdEdge]:
        return self.engine.compute_identical_id_edges(df)

    def compute_prerequisite_edges(
        self, df: pd.DataFrame, course_embeddings: np.ndarray, threshold: float = 0.7
    ) -> Tuple[List[PrereqEdge], dict]:
        return self.engine.compute_prerequisite_edges(df, course_embeddings, threshold=threshold)

    # ── 영속성 (GraphWriter 위임) ─────────────────────────────────────
    def clear_database(self) -> None:
        self.writer.clear_database()

    def create_graph(
        self,
        df: pd.DataFrame,
        edges: List[SimilarityEdge],
        identical_edges: Optional[List[IdenticalIdEdge]] = None,
        prereq_edges: Optional[List[PrereqEdge]] = None,
        unmapped_prereqs: Optional[dict] = None,
    ) -> None:
        self.writer.create_graph(df, edges, identical_edges, prereq_edges, unmapped_prereqs)

    def create_indexes(self) -> None:
        self.writer.create_indexes()

    # ── 조회 (GraphReader 위임) ───────────────────────────────────────
    def get_statistics(self) -> dict:
        return self.reader.get_statistics()

    def find_similar_courses(self, course_name: str, top_k: int = 10) -> List[dict]:
        return self.reader.find_similar_courses(course_name, top_k=top_k)


def main() -> None:
    """standalone 실행: 설정을 env(Settings)에서 읽어 전체 파이프라인을 수행."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings.from_env()

    print("=" * 80)
    print("교과목 유사도 그래프 네트워크 구축")
    print("=" * 80)

    builder = CourseGraphBuilder(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password,
        hybrid_weight=settings.hybrid_weight,
    )
    try:
        df = builder.load_course_data(settings.csv_path)
        embeddings = builder.create_embeddings(df)
        edges = builder.compute_similarity(df, embeddings, threshold=settings.similarity_threshold)
        identical_edges = builder.compute_identical_id_edges(df)
        prereq_edges, unmapped = builder.compute_prerequisite_edges(
            df, embeddings, threshold=settings.prereq_threshold
        )

        builder.create_graph(df, edges, identical_edges, prereq_edges, unmapped)
        builder.create_indexes()

        stats = builder.get_statistics()
        print(f"\n교과목 수: {stats['num_courses']}")
        print(f"유사도 엣지(SIMILAR_TO): {stats['num_edges']}")
        print(f"선수강 엣지(REQUIRES): {stats['num_requires']}")
        print(f"평균/최대/최소 유사도: "
              f"{stats['avg_similarity']:.4f} / {stats['max_similarity']:.4f} / {stats['min_similarity']:.4f}")
    finally:
        builder.close()

    print("\n" + "=" * 80)
    print("그래프 구축 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
