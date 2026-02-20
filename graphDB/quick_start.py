#!/usr/bin/env python3
"""
교과목 그래프 네트워크 - 빠른 시작 예제

Neo4j가 이미 실행 중이어야 합니다.
Docker: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
"""

from course_similarity_graph import CourseGraphBuilder
from course_graph_analysis import CourseGraphAnalyzer

import os

def quick_start_example():
    """빠른 시작 예제"""
    
    # === 설정 ===
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")
    CSV_PATH = "final_course.csv"
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
        
        # 그래프 생성
        print("Neo4j 그래프 생성 중...")
        builder.clear_database()  # 기존 데이터 삭제
        builder.create_graph(df, edges, identical_edges)
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
    
    # === 2단계: 그래프 분석 ===
    print("\n[2단계] 그래프 분석 예제")
    print("-" * 80)
    
    analyzer = CourseGraphAnalyzer(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # 예제 1: 연결 중심성 분석
        print("\n[예제 1] 가장 많은 교과목과 연결된 교과목 Top 5")
        central = analyzer.get_course_degree_centrality(top_k=5)
        for i, course in enumerate(central, 1):
            print(f"  {i}. {course['name']} - {course['connections']}개 연결")
        
        # 예제 2: 유사 교과목 추천
        print("\n[예제 2] 첫 번째 교과목과 유사한 교과목")
        first_course = df.iloc[0]['교과목 이름']
        print(f"기준 교과목: {first_course}")
        similar = analyzer.recommend_by_similarity(first_course, top_k=5)
        for i, course in enumerate(similar, 1):
            dept_info = f" ({course.get('department', 'N/A')})" if course.get('department') else ""
            print(f"  {i}. {course['name']}{dept_info} - 유사도: {course['similarity']:.4f}")
        
        # 예제 3: 키워드 검색
        print("\n[예제 3] '프로그래밍' 키워드 검색")
        results = analyzer.search_courses('프로그래밍')
        for i, course in enumerate(results[:5], 1):
            dept_info = f" - {course.get('department', 'N/A')}" if course.get('department') else ""
            print(f"  {i}. {course['name']} ({course['code']}){dept_info}")
        
        # 예제 4: 교과과정 구조 분석
        print("\n[예제 4] 전체 교과과정 구조")
        structure = analyzer.analyze_curriculum_structure()
        print(f"총 교과목 수: {structure['total_courses']}")
        print(f"이수구분별 통계 (상위 5개):")
        for cat in structure['categories'][:5]:
            print(f"  - {cat['category']}: {cat['course_count']}과목")
        
        # 예제 5: 동일 학수번호 과목 분석 (새로운 기능)
        print("\n[예제 5] 동일 학수번호/다른 학과 과목 분석")
        shared_ids = analyzer.get_shared_course_ids(top_k=5)
        if shared_ids:
            print("여러 학과에서 공유하는 학수번호 Top 5:")
            for i, item in enumerate(shared_ids, 1):
                print(f"  {i}. {item['course_code']} - {item['dept_count']}개 학과: {', '.join(item['departments'][:3])}...")
        else:
            print("동일 학수번호/다른 학과 과목이 없습니다.")
        
        # 예제 6: 특정 과목의 동일 학수번호 과목 찾기
        if len(identical_edges) > 0:
            print("\n[예제 6] 특정 과목의 동일 학수번호 과목")
            sample_idx = identical_edges[0][0]
            sample_course = df.iloc[sample_idx]['교과목 이름']
            sample_dept = df.iloc[sample_idx]['설강학과']
            print(f"기준 과목: {sample_course} ({sample_dept})")
            
            identical_courses = analyzer.find_identical_id_courses(sample_course)
            if identical_courses:
                # 학과별로 그룹핑하여 중복 제거
                unique_depts = {}
                for course in identical_courses:
                    dept = course['department']
                    if dept not in unique_depts:
                        unique_depts[dept] = course
                
                print(f"동일 학수번호 과목 ({len(unique_depts)}개 학과):")
                for i, (dept, course) in enumerate(list(unique_depts.items())[:5], 1):
                    print(f"  {i}. {course['name']} - {dept} (학수번호: {course['code']})")
                
                if len(unique_depts) > 5:
                    print(f"  ... 외 {len(unique_depts) - 5}개 학과")
            else:
                print("동일 학수번호를 가진 다른 학과 과목이 없습니다.")
        
    finally:
        analyzer.close()
    
    print("\n" + "=" * 80)
    print("완료! Neo4j Browser (http://localhost:7474)에서 그래프를 확인하세요.")
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
""")


if __name__ == "__main__":
    quick_start_example()