"""
GraphRAG를 활용한 교과목 분석 및 추천 시스템
"""

from neo4j import GraphDatabase
from typing import List, Dict
import pandas as pd


class CourseGraphAnalyzer:
    """교과목 그래프 분석 및 추천 클래스"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    # ========== 기본 그래프 분석 ==========
    
    def get_course_degree_centrality(self, top_k: int = 20) -> List[Dict]:
        """
        연결 중심성(Degree Centrality) 분석
        가장 많은 교과목과 유사한 교과목 찾기
        
        Args:
            top_k: 상위 k개 반환
            
        Returns:
            교과목 리스트 (이름, 학수번호, 연결 개수)
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Course)-[r:SIMILAR_TO]-()
                WITH c, count(r) as connections
                RETURN c.name as name, 
                       c.code as code,
                       c.category as category,
                       c.department as department,
                       connections
                ORDER BY connections DESC
                LIMIT $top_k
                """,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    def get_course_communities(self, similarity_threshold: float = 0.7) -> List[Dict]:
        """
        유사도 기반 교과목 커뮤니티 탐지
        높은 유사도를 가진 교과목 군집 찾기
        
        Args:
            similarity_threshold: 커뮤니티 형성 최소 유사도
            
        Returns:
            커뮤니티별 교과목 그룹
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c1:Course)-[r:SIMILAR_TO]-(c2:Course)
                WHERE r.similarity >= $threshold
                WITH c1, collect(DISTINCT c2.name) as similar_courses, 
                     count(DISTINCT c2) as cluster_size
                WHERE cluster_size >= 3
                RETURN c1.name as course_name,
                       c1.code as code,
                       similar_courses,
                       cluster_size
                ORDER BY cluster_size DESC
                """,
                threshold=similarity_threshold
            )
            return [dict(record) for record in result]
    
    def get_course_path(self, start_course: str, end_course: str, max_hops: int = 3) -> List[Dict]:
        """
        두 교과목 간의 유사도 경로 찾기
        
        Args:
            start_course: 시작 교과목 이름
            end_course: 목표 교과목 이름
            max_hops: 최대 홉 수
            
        Returns:
            경로 정보
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = shortestPath(
                    (start:Course {name: $start})-[:SIMILAR_TO*..{max_hops}]-(end:Course {name: $end})
                )
                RETURN [node in nodes(path) | node.name] as course_path,
                       [rel in relationships(path) | rel.similarity] as similarities,
                       length(path) as path_length
                """.replace('{max_hops}', str(max_hops)),
                start=start_course,
                end=end_course
            )
            return [dict(record) for record in result]
    
    # ========== 교과목 추천 시스템 ==========
    
    def recommend_by_similarity(self, course_name: str, 
                                top_k: int = 10, 
                                min_similarity: float = 0.5) -> List[Dict]:
        """
        특정 교과목과 유사한 교과목 추천
        
        Args:
            course_name: 기준 교과목 이름
            top_k: 추천 개수
            min_similarity: 최소 유사도
            
        Returns:
            추천 교과목 리스트
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c1:Course {name: $name})-[r:SIMILAR_TO]-(c2:Course)
                WHERE r.similarity >= $min_sim
                WITH DISTINCT c2.name as name,
                     c2.code as code,
                     c2.department as department,
                     c2.category as category,
                     c2.credits as credits,
                     c2.summary as summary,
                     max(r.similarity) as similarity
                RETURN name, code, department, category, credits, summary, similarity
                ORDER BY similarity DESC
                LIMIT $top_k
                """,
                name=course_name,
                top_k=top_k,
                min_sim=min_similarity
            )
            return [dict(record) for record in result]
    
    def find_identical_id_courses(self, course_name: str) -> List[Dict]:
        """
        동일한 학수번호를 가진 다른 학과의 교과목 찾기
        (학수번호는 같으나 설강학과가 다른 과목)
        
        Args:
            course_name: 기준 교과목 이름
            
        Returns:
            동일 학수번호 교과목 리스트
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c1:Course {name: $name})-[r:IDENTICAL_ID]-(c2:Course)
                RETURN c2.name as name,
                       c2.code as code,
                       c2.department as department,
                       c1.department as original_department,
                       r.note as note
                ORDER BY c2.department
                """,
                name=course_name
            )
            return [dict(record) for record in result]
    
    def get_shared_course_ids(self, top_k: int = 20) -> List[Dict]:
        """
        여러 학과에서 공유하는 학수번호 통계
        
        Args:
            top_k: 상위 k개 반환
            
        Returns:
            학수번호별 공유 학과 정보
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
                WITH c.code as course_code,
                     collect(DISTINCT c.department) + collect(DISTINCT c2.department) as departments,
                     count(DISTINCT r) as share_count
                RETURN course_code,
                       departments,
                       size(departments) as dept_count,
                       share_count
                ORDER BY dept_count DESC, share_count DESC
                LIMIT $top_k
                """,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    def recommend_by_multiple_courses(self, course_names: List[str], 
                                     top_k: int = 10) -> List[Dict]:
        """
        여러 교과목을 수강한 학생에게 다음 교과목 추천
        
        Args:
            course_names: 이미 수강한 교과목 리스트
            top_k: 추천 개수
            
        Returns:
            추천 교과목 리스트
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (taken:Course)-[r:SIMILAR_TO]-(recommended:Course)
                WHERE taken.name IN $taken_courses
                  AND NOT recommended.name IN $taken_courses
                WITH recommended, avg(r.similarity) as avg_similarity, count(*) as common_connections
                RETURN recommended.name as name,
                       recommended.code as code,
                       recommended.category as category,
                       recommended.summary as summary,
                       avg_similarity,
                       common_connections
                ORDER BY avg_similarity DESC, common_connections DESC
                LIMIT $top_k
                """,
                taken_courses=course_names,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    def recommend_by_department(self, department: str, 
                               taken_courses: List[str] = None,
                               top_k: int = 10) -> List[Dict]:
        """
        특정 학과의 교과목 중 추천
        
        Args:
            department: 학과명
            taken_courses: 이미 수강한 교과목 (선택)
            top_k: 추천 개수
            
        Returns:
            추천 교과목 리스트
        """
        taken_courses = taken_courses or []
        
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Course)
                WHERE c.department CONTAINS $dept
                  AND NOT c.name IN $taken
                OPTIONAL MATCH (c)-[r:SIMILAR_TO]-()
                WITH c, avg(r.similarity) as avg_connectivity, count(r) as connections
                RETURN c.name as name,
                       c.code as code,
                       c.category as category,
                       c.credits as credits,
                       c.summary as summary,
                       avg_connectivity,
                       connections
                ORDER BY avg_connectivity DESC, connections DESC
                LIMIT $top_k
                """,
                dept=department,
                taken=taken_courses,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    # ========== 교과과정 분석 ==========
    
    def analyze_curriculum_structure(self, department: str = None) -> Dict:
        """
        교과과정 구조 분석
        
        Args:
            department: 분석할 학과 (None이면 전체)
            
        Returns:
            교과과정 통계
        """
        with self.driver.session() as session:
            dept_filter = "WHERE c.department CONTAINS $dept" if department else ""
            
            result = session.run(
                f"""
                MATCH (c:Course)
                {dept_filter}
                WITH c.category as category, 
                     count(*) as course_count,
                     avg(c.credits) as avg_credits
                RETURN category, course_count, avg_credits
                ORDER BY course_count DESC
                """,
                dept=department or ""
            )
            
            categories = [dict(record) for record in result]
            
            # 전체 통계
            total_result = session.run(
                f"""
                MATCH (c:Course)
                {dept_filter}
                RETURN count(*) as total_courses,
                       sum(c.credits) as total_credits,
                       avg(c.credits) as avg_credits
                """,
                dept=department or ""
            )
            
            total_stats = total_result.single()
            
            return {
                'department': department or '전체',
                'total_courses': total_stats['total_courses'],
                'total_credits': total_stats['total_credits'],
                'avg_credits': total_stats['avg_credits'],
                'categories': categories
            }
    
    def find_prerequisite_patterns(self, top_k: int = 20) -> List[Dict]:
        """
        선수과목 패턴 분석
        유사도가 높은 교과목 쌍에서 학년 차이가 있는 경우 찾기
        
        Returns:
            선수과목 후보 리스트
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c1:Course)-[r:SIMILAR_TO]-(c2:Course)
                WHERE r.similarity >= 0.6
                  AND c1.year < c2.year
                RETURN c1.name as prerequisite,
                       c1.code as prereq_code,
                       c2.name as advanced_course,
                       c2.code as advanced_code,
                       r.similarity as similarity,
                       c2.year - c1.year as year_gap
                ORDER BY r.similarity DESC
                LIMIT $top_k
                """,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    # ========== 검색 및 필터링 ==========
    
    def search_courses(self, keyword: str, category: str = None) -> List[Dict]:
        """
        키워드로 교과목 검색
        
        Args:
            keyword: 검색 키워드
            category: 이수구분 필터 (선택)
            
        Returns:
            검색 결과
        """
        with self.driver.session() as session:
            category_filter = "AND c.category = $category" if category else ""
            
            result = session.run(
                f"""
                MATCH (c:Course)
                WHERE c.name CONTAINS $keyword 
                   OR c.summary CONTAINS $keyword
                   {category_filter}
                RETURN c.name as name,
                       c.code as code,
                       c.category as category,
                       c.credits as credits,
                       c.department as department,
                       c.summary as summary
                ORDER BY c.name
                """,
                keyword=keyword,
                category=category or ""
            )
            return [dict(record) for record in result]


# ========== 사용 예제 ==========

def example_usage():
    """사용 예제"""
    
    analyzer = CourseGraphAnalyzer(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="your_password"
    )
    
    try:
        print("=" * 80)
        print("교과목 그래프 분석 예제")
        print("=" * 80)
        
        # 1. 연결 중심성 분석
        print("\n[1] 가장 많은 교과목과 연결된 교과목 Top 10")
        central_courses = analyzer.get_course_degree_centrality(top_k=10)
        for i, course in enumerate(central_courses, 1):
            print(f"{i}. {course['name']} ({course['code']}) - {course['connections']} 연결")
        
        # 2. 유사 교과목 추천
        print("\n[2] '데이터베이스' 교과목과 유사한 교과목 추천")
        similar = analyzer.recommend_by_similarity('데이터베이스', top_k=5)
        for i, course in enumerate(similar, 1):
            print(f"{i}. {course['name']} - 유사도: {course['similarity']:.4f}")
        
        # 3. 여러 교과목 기반 추천
        print("\n[3] 복수 교과목 기반 추천")
        taken = ['자료구조', '알고리즘']
        recommendations = analyzer.recommend_by_multiple_courses(taken, top_k=5)
        for i, course in enumerate(recommendations, 1):
            print(f"{i}. {course['name']} - 평균 유사도: {course['avg_similarity']:.4f}")
        
        # 4. 교과과정 구조 분석
        print("\n[4] 컴퓨터공학 교과과정 구조")
        structure = analyzer.analyze_curriculum_structure('컴퓨터')
        print(f"총 교과목 수: {structure['total_courses']}")
        print(f"평균 학점: {structure['avg_credits']:.2f}")
        print("\n이수구분별 통계:")
        for cat in structure['categories'][:5]:
            print(f"  - {cat['category']}: {cat['course_count']}과목 (평균 {cat['avg_credits']:.1f}학점)")
        
        # 5. 키워드 검색
        print("\n[5] '머신러닝' 키워드 검색")
        search_results = analyzer.search_courses('머신러닝')
        for i, course in enumerate(search_results[:5], 1):
            print(f"{i}. {course['name']} ({course['code']}) - {course['category']}")
        
    finally:
        analyzer.close()


if __name__ == "__main__":
    example_usage()
