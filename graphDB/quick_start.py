#!/usr/bin/env python3
"""
교과목 그래프 네트워크 - 빠른 시작 / 재구축 진입점.

이 파일은 backend(ai/tasks.py)의 rebuild_graph 태스크가
`uv run python quick_start.py` (cwd=/graphDB) 로 호출하는 **동결 진입점**이다.
파일명·실행 방식·CSV 상대경로 전제를 유지한다.

Neo4j 가 실행 중이어야 한다.
Docker: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
"""

import logging

from config import Settings
from course_graph_analysis import run_validation_report
from course_similarity_graph import CourseGraphBuilder

logger = logging.getLogger(__name__)


def quick_start_example() -> None:
    settings = Settings.from_env()

    print("=" * 80)
    print("교과목 유사도 그래프 네트워크 - 빠른 시작")
    print("=" * 80)

    # === 1단계: 그래프 구축 ===
    print("\n[1단계] 그래프 구축")
    print("-" * 80)

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

        builder.clear_database()  # 기존 데이터 삭제 후 재구축
        builder.create_graph(df, edges, identical_edges, prereq_edges, unmapped)
        builder.create_indexes()

        stats = builder.get_statistics()
        print("\n그래프 통계:")
        print(f"  - 교과목 수: {stats['num_courses']}")
        print(f"  - 엣지 수: {stats['num_edges']}")
        print(f"  - 평균 유사도: {stats['avg_similarity']:.4f}")
    finally:
        builder.close()

    # === 2단계: 그래프 검증 및 분석 ===
    print("\n[2단계] 그래프 분석 검증 리포트 생성")
    print("-" * 80)
    try:
        run_validation_report(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    except Exception as e:
        print(f"검증 리포트 생성 실패: {e}")

    print("\n" + "=" * 80)
    print("완료! Neo4j 데이터베이스가 구축되었습니다.")
    print("=" * 80)
    _print_sample_queries()


def _print_sample_queries() -> None:
    print("\n추천 Cypher 쿼리:")
    print("-" * 80)
    print("""
# 1. 전체 그래프 보기 (샘플)
MATCH (c:Course)-[r:SIMILAR_TO]-(c2:Course)
WHERE r.similarity >= 0.7
RETURN c, r, c2
LIMIT 100

# 2. 특정 교과목의 유사 교과목 (의미적 유사도)
MATCH (c:Course {name: '데이터베이스'})-[r:SIMILAR_TO]-(c2:Course)
RETURN c2.name, r.similarity
ORDER BY r.similarity DESC
LIMIT 10

# 3. 동일 학수번호/다른 학과 과목 찾기
MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
RETURN c.name as course1, c.department as dept1,
       c2.name as course2, c2.department as dept2,
       c.code as shared_code
LIMIT 20

# 4. 선수강과목(Prerequisite) 매핑 결과
MATCH (c1:Course)-[r:REQUIRES]->(c2:Course)
RETURN c1.name as source_course, c1.department as dept,
       c2.name as required_course, r.raw_text as raw_text, r.similarity as sim
ORDER BY sim DESC
LIMIT 10
""")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    quick_start_example()
