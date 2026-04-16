"""
교과목 그래프 오프라인 분석 스크립트
======================================
이 파일은 graphDB 파이프라인 전용 분석/검증 도구입니다.
백엔드 API 서빙과는 무관하며, 그래프 구축 결과를 로컬에서 검증할 때 사용합니다.

[역할 분리]
- course_similarity_graph.py : 그래프 구축 (CSV → Neo4j 쓰기)
- course_graph_analysis.py   : 그래프 검증 (Neo4j 읽기, 오프라인 전용)  ← 이 파일
- backend/services/graph_service.py : 런타임 API 서빙 (Neo4j 읽기, 백엔드 전용)

[중복 제거 이력]
이전에는 CourseGraphAnalyzer가 backend/services/graph_service.py의
CourseGraphService와 거의 동일한 Cypher 쿼리를 중복 구현하고 있었습니다.
백엔드 서빙 로직은 graph_service.py로 일원화하고,
이 파일은 graphDB 파이프라인 고유의 분석 기능만 유지합니다.

  graphDB 고유 분석:
  - 임계값별 엣지 분포 분석 (threshold sensitivity)
  - REQUIRES 엣지 매핑 품질 검증 (미매핑 과목 통계)
  - 그래프 구축 결과 종합 리포트
  - 연결 컴포넌트 분석
"""

from neo4j import GraphDatabase
from typing import List, Dict, Optional
import pandas as pd


class CourseGraphValidator:
    """
    그래프 구축 결과 검증 클래스 (오프라인 전용)

    course_similarity_graph.py 실행 후 Neo4j에 생성된 그래프의
    품질과 통계를 검증하는 용도로 사용합니다.
    """

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ───────────────────────────────────────────────────────
    # 1. 그래프 구축 결과 기본 통계
    # ───────────────────────────────────────────────────────

    def get_build_summary(self) -> Dict:
        """
        그래프 구축 결과 종합 요약

        Returns:
            노드 수, 엣지 타입별 수, 평균 유사도, REQUIRES 매핑 통계
        """
        with self.driver.session() as session:
            node_result = session.run(
                "MATCH (c:Course) RETURN count(c) as num_courses"
            ).single()

            sim_result = session.run(
                """
                MATCH ()-[r:SIMILAR_TO]->()
                RETURN count(r) as num_sim_edges,
                       avg(r.similarity) as avg_sim,
                       min(r.similarity) as min_sim,
                       max(r.similarity) as max_sim
                """
            ).single()

            id_result = session.run(
                "MATCH ()-[r:IDENTICAL_ID]->() RETURN count(r) as num_id_edges"
            ).single()

            req_result = session.run(
                """
                MATCH ()-[r:REQUIRES]->()
                RETURN count(r) as num_req_edges,
                       avg(r.similarity) as avg_confidence,
                       sum(CASE WHEN r.similarity = 1.0 THEN 1 ELSE 0 END) as exact_matches,
                       sum(CASE WHEN r.similarity < 1.0 THEN 1 ELSE 0 END) as semantic_matches
                """
            ).single()

            unmapped_result = session.run(
                """
                MATCH (c:Course)
                WHERE c.unmapped_prerequisites IS NOT NULL
                  AND c.unmapped_prerequisites <> ''
                RETURN count(c) as courses_with_unmapped,
                       collect(c.name)[..10] as sample_courses
                """
            ).single()

        return {
            "node": {
                "num_courses": node_result["num_courses"],
            },
            "similar_to": {
                "num_edges": sim_result["num_sim_edges"],
                "avg_similarity": round(sim_result["avg_sim"] or 0, 4),
                "min_similarity": round(sim_result["min_sim"] or 0, 4),
                "max_similarity": round(sim_result["max_sim"] or 0, 4),
            },
            "identical_id": {
                "num_edges": id_result["num_id_edges"],
            },
            "requires": {
                "num_edges": req_result["num_req_edges"],
                "avg_confidence": round(req_result["avg_confidence"] or 0, 4),
                "exact_matches": req_result["exact_matches"],
                "semantic_matches": req_result["semantic_matches"],
            },
            "unmapped_prerequisites": {
                "courses_count": unmapped_result["courses_with_unmapped"],
                "sample": unmapped_result["sample_courses"],
            },
        }

    # ───────────────────────────────────────────────────────
    # 2. 임계값 민감도 분석 (graphDB 파이프라인 고유)
    # ───────────────────────────────────────────────────────

    def analyze_threshold_sensitivity(
        self, thresholds: List[float] = None
    ) -> List[Dict]:
        """
        유사도 임계값별 생성 엣지 수 분포 분석

        그래프 구축 시 적절한 threshold를 결정하거나,
        현재 그래프의 threshold 선택이 적절했는지 사후 검증합니다.

        Args:
            thresholds: 분석할 임계값 목록 (기본: 0.5 ~ 0.9)

        Returns:
            [{threshold, num_edges, coverage_rate}, ...]
        """
        if thresholds is None:
            thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]

        results = []
        with self.driver.session() as session:
            total_result = session.run(
                "MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as total"
            ).single()
            total_edges = total_result["total"] or 1  # 0 division 방지

            for threshold in thresholds:
                result = session.run(
                    """
                    MATCH ()-[r:SIMILAR_TO]->()
                    WHERE r.similarity >= $threshold
                    RETURN count(r) as num_edges
                    """,
                    threshold=threshold,
                ).single()
                num_edges = result["num_edges"]
                results.append({
                    "threshold": threshold,
                    "num_edges": num_edges,
                    "coverage_rate": round(num_edges / total_edges * 100, 1),
                })

        return results

    # ───────────────────────────────────────────────────────
    # 3. REQUIRES 매핑 품질 검증 (graphDB 파이프라인 고유)
    # ───────────────────────────────────────────────────────

    def get_unmapped_prerequisites(self, limit: int = 50) -> List[Dict]:
        """
        매핑에 실패한 선수강 과목 텍스트 조회

        graphDB 파이프라인에서 Exact/Semantic 매핑 모두 실패한
        선수강 과목 원문 텍스트를 조회합니다.
        이 데이터를 기반으로 stopwords나 매핑 임계값을 조정할 수 있습니다.

        Args:
            limit: 최대 반환 수

        Returns:
            [{course_name, unmapped_text}, ...]
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Course)
                WHERE c.unmapped_prerequisites IS NOT NULL
                  AND c.unmapped_prerequisites <> ''
                RETURN c.name as course_name,
                       c.unmapped_prerequisites as unmapped_text
                ORDER BY c.name
                LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(record) for record in result]

    def get_requires_mapping_quality(self) -> Dict:
        """
        REQUIRES 엣지 매핑 품질 상세 통계

        Returns:
            exact/semantic 비율, 신뢰도 분포
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH ()-[r:REQUIRES]->()
                WITH r.similarity as conf
                RETURN
                    count(*) as total,
                    sum(CASE WHEN conf = 1.0 THEN 1 ELSE 0 END) as exact,
                    sum(CASE WHEN conf >= 0.8 AND conf < 1.0 THEN 1 ELSE 0 END) as high,
                    sum(CASE WHEN conf >= 0.6 AND conf < 0.8 THEN 1 ELSE 0 END) as medium,
                    sum(CASE WHEN conf < 0.6 THEN 1 ELSE 0 END) as low,
                    avg(conf) as avg_confidence
                """
            ).single()

            if not result or result["total"] == 0:
                return {"total": 0}

            total = result["total"]
            return {
                "total": total,
                "exact_match": {"count": result["exact"],
                                "rate": round(result["exact"] / total * 100, 1)},
                "high_confidence": {"count": result["high"],
                                    "rate": round(result["high"] / total * 100, 1)},
                "medium_confidence": {"count": result["medium"],
                                      "rate": round(result["medium"] / total * 100, 1)},
                "low_confidence": {"count": result["low"],
                                   "rate": round(result["low"] / total * 100, 1)},
                "avg_confidence": round(result["avg_confidence"] or 0, 4),
            }

    # ───────────────────────────────────────────────────────
    # 4. 연결 컴포넌트 분석 (graphDB 파이프라인 고유)
    # ───────────────────────────────────────────────────────

    def get_isolated_courses(self) -> List[Dict]:
        """
        SIMILAR_TO 관계가 전혀 없는 고립 노드 조회

        유사도가 낮아 어떤 과목과도 연결되지 않은 과목들입니다.
        그래프 구축 임계값 조정이나 데이터 보완이 필요할 수 있습니다.

        Returns:
            [{name, code, department, category}, ...]
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Course)
                WHERE NOT (c)-[:SIMILAR_TO]-()
                RETURN c.name       as name,
                       c.code       as code,
                       c.department as department,
                       c.category   as category
                ORDER BY c.department, c.name
                """
            )
            return [dict(record) for record in result]

    def get_highly_connected_courses(self, top_k: int = 20) -> List[Dict]:
        """
        연결 수가 가장 많은 과목 (허브 과목) 조회

        허브 과목은 많은 과목과 유사성을 가지는 핵심 과목으로,
        교육과정에서 중심적인 역할을 할 가능성이 높습니다.

        Args:
            top_k: 상위 반환 수

        Returns:
            [{name, code, department, connections}, ...]
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Course)-[r:SIMILAR_TO]-()
                WITH c, count(r) as connections
                RETURN c.name       as name,
                       c.code       as code,
                       c.department as department,
                       c.category   as category,
                       connections
                ORDER BY connections DESC
                LIMIT $top_k
                """,
                top_k=top_k,
            )
            return [dict(record) for record in result]


# ───────────────────────────────────────────────────────────────
# 실행 예제 (standalone 검증용)
# ───────────────────────────────────────────────────────────────

def run_validation_report(
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "your_password",
):
    """
    그래프 구축 결과 전체 검증 리포트 출력

    course_similarity_graph.py 실행 후 이 함수를 호출하여
    그래프 품질을 확인합니다.
    """
    validator = CourseGraphValidator(uri, user, password)

    try:
        print("=" * 70)
        print("교과목 그래프 구축 결과 검증 리포트")
        print("=" * 70)

        # 1. 기본 통계
        print("\n[1] 그래프 구축 요약")
        summary = validator.get_build_summary()
        print(f"  교과목(노드) 수:         {summary['node']['num_courses']}")
        print(f"  SIMILAR_TO 엣지 수:     {summary['similar_to']['num_edges']}")
        print(f"  IDENTICAL_ID 엣지 수:   {summary['identical_id']['num_edges']}")
        print(f"  REQUIRES 엣지 수:       {summary['requires']['num_edges']}")
        print(f"  평균 유사도:             {summary['similar_to']['avg_similarity']}")
        print(f"  선수강 미매핑 과목 수:   {summary['unmapped_prerequisites']['courses_count']}")

        # 2. 임계값 민감도
        print("\n[2] 유사도 임계값별 엣지 수 분포")
        sensitivity = validator.analyze_threshold_sensitivity()
        for row in sensitivity:
            bar = "█" * int(row["coverage_rate"] / 5)
            print(f"  threshold={row['threshold']:.2f}: {row['num_edges']:6d}개 "
                  f"({row['coverage_rate']:5.1f}%) {bar}")

        # 3. REQUIRES 매핑 품질
        print("\n[3] 선수강 매핑 품질")
        quality = validator.get_requires_mapping_quality()
        if quality.get("total", 0) > 0:
            print(f"  전체: {quality['total']} 엣지")
            print(f"  - Exact match:        {quality['exact_match']['count']} ({quality['exact_match']['rate']}%)")
            print(f"  - High confidence:    {quality['high_confidence']['count']} ({quality['high_confidence']['rate']}%)")
            print(f"  - Medium confidence:  {quality['medium_confidence']['count']} ({quality['medium_confidence']['rate']}%)")
            print(f"  - Low confidence:     {quality['low_confidence']['count']} ({quality['low_confidence']['rate']}%)")
        else:
            print("  REQUIRES 엣지가 없습니다.")

        # 4. 미매핑 선수강 샘플
        print("\n[4] 매핑 실패 선수강 과목 샘플 (최대 10개)")
        unmapped = validator.get_unmapped_prerequisites(limit=10)
        if unmapped:
            for item in unmapped:
                print(f"  [{item['course_name']}] → {item['unmapped_text']}")
        else:
            print("  미매핑 과목이 없습니다.")

        # 5. 고립 노드
        print("\n[5] 고립 노드 (SIMILAR_TO 관계 없는 과목)")
        isolated = validator.get_isolated_courses()
        print(f"  총 {len(isolated)}개")
        for course in isolated[:5]:
            print(f"  - {course['name']} ({course['code']}) / {course['department']}")
        if len(isolated) > 5:
            print(f"  ... 외 {len(isolated) - 5}개")

        print("\n" + "=" * 70)
        print("검증 완료")
        print("=" * 70)

    finally:
        validator.close()


if __name__ == "__main__":
    run_validation_report(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="your_password",  # 실제 비밀번호로 변경
    )
