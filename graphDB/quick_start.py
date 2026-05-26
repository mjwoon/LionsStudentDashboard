#!/usr/bin/env python3
"""
교과목 그래프 네트워크 - 빠른 시작 예제

Neo4j가 이미 실행 중이어야 합니다.
Docker: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
"""

from course_similarity_graph import CourseGraphBuilder
from course_graph_analysis import run_validation_report

import os

def quick_start_example():
    """빠른 시작 예제"""
    
    # === 설정 ===
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")
    CSV_PATH = "course_all_aggregated.csv"
    SIMILARITY_THRESHOLD = 0.5  # 유사도 임계값
    
    print("=" * 80)
    print("교과목 유사도 그래프 네트워크 - 빠른 시작")
    print("=" * 80)
    
    # === 1단계: 그래프 구축 ===
    print("\n[1단계] 그래프 구축")
    print("-" * 80)
    
    builder = CourseGraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # 데이터 로드
        print("데이터 로드 중...")
        df = builder.load_course_data(CSV_PATH)
        print(f"✓ {len(df)}개 교과목 로드 완료\n")
        
        # 임베딩 생성
        print("임베딩 생성 중...")
        embeddings = builder.create_embeddings(df)
        print(f"✓ 임베딩 생성 완료 (shape: {embeddings.shape})\n")
        
        # 유사도 계산
        print(f"유사도 계산 중... (임계값: {SIMILARITY_THRESHOLD})")
        edges = builder.compute_similarity(df, embeddings, threshold=SIMILARITY_THRESHOLD)
        print(f"✓ {len(edges)}개 엣지 생성 완료\n")
        
        # 학수번호 기반 엣지 계산
        print("학수번호 기반 관계 계산 중... (동일 학수번호, 다른 학과)")
        identical_edges = builder.compute_identical_id_edges(df)
        print(f"✓ {len(identical_edges)}개 동일 학수번호 관계 생성 완료\n")
        
        # 선수강과목 매핑
        print("선수강과목 파싱 및 매핑 중...")
        prereq_edges, unmapped_prereqs = builder.compute_prerequisite_edges(df, embeddings, threshold=0.6)
        print(f"✓ {len(prereq_edges)}개 엣지 생성 및 Unmapped 데이터 분류 완료\n")
        
        # 그래프 생성
        print("Neo4j 그래프 생성 중...")
        builder.clear_database()  # 기존 데이터 삭제
        builder.create_graph(df, edges, identical_edges, prereq_edges, unmapped_prereqs)
        builder.create_indexes()
        print("✓ 그래프 생성 완료\n")
        
        # 통계
        stats = builder.get_statistics()
        print("그래프 통계:")
        print(f"  - 교과목 수: {stats['num_courses']}")
        print(f"  - 엣지 수: {stats['num_edges']}")
        print(f"  - 평균 유사도: {stats['avg_similarity']:.4f}")
        
    finally:
        builder.close()
    
    # === 2단계: 그래프 검증 및 분석 ===
    print("\n[2단계] 그래프 분석 검증 리포트 생성")
    print("-" * 80)
    
    try:
        run_validation_report(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    except Exception as e:
        print(f"검증 리포트 생성 실패: {e}")
    
    print("\n" + "=" * 80)
    print("완료! Neo4j Aura 데이터베이스가 구축되었습니다.")
    print("=" * 80)
    
    # Cypher 쿼리 예제 출력
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

# 3. 동일 학수번호/다른 학과 과목 찾기 (NEW!)
MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
RETURN c.name as course1, c.department as dept1,
       c2.name as course2, c2.department as dept2,
       c.code as shared_code
LIMIT 20

# 4. 특정 학과의 네트워크
MATCH (c:Course)
WHERE c.department CONTAINS '컴퓨터'
OPTIONAL MATCH (c)-[r:SIMILAR_TO]-(c2:Course)
WHERE c2.department CONTAINS '컴퓨터'
RETURN c, r, c2

# 5. 학수번호로 공유되는 과목 통계
MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
WITH c.code as course_code, 
     collect(DISTINCT c.department) + collect(DISTINCT c2.department) as depts
RETURN course_code, depts, size(depts) as dept_count
ORDER BY dept_count DESC
LIMIT 10

# 6. 선수강과목(Prerequisite) 매핑 결과 (NEW!)
MATCH (c1:Course)-[r:REQUIRES]->(c2:Course)
RETURN c1.name as source_course, c1.department as dept, 
       c2.name as required_course, r.raw_text as raw_text, r.similarity as sim
ORDER BY sim DESC
LIMIT 10
""")


if __name__ == "__main__":
    quick_start_example()