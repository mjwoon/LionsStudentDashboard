"""
Neo4j 그래프 데이터베이스 서비스
교과목 유사도 기반 그래프 분석 및 추천 기능 제공
"""

import os
from typing import List, Dict, Optional
from neo4j import GraphDatabase
from contextlib import contextmanager


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
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            user = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD', 'password123')
            cls._driver = GraphDatabase.driver(uri, auth=(user, password))
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


class CourseGraphService:
    """교과목 그래프 분석 서비스"""
    
    # ==================== 기본 통계 ====================
    
    @staticmethod
    def get_graph_statistics() -> Dict:
        """그래프 전체 통계 조회"""
        with get_session() as session:
            result = session.run(
                """
                MATCH (c:Course)
                OPTIONAL MATCH (c)-[r:SIMILAR_TO]-()
                OPTIONAL MATCH (c)-[i:IDENTICAL_ID]-()
                RETURN 
                    count(DISTINCT c) as num_courses,
                    count(DISTINCT r) / 2 as num_similarity_edges,
                    count(DISTINCT i) / 2 as num_identical_edges,
                    avg(r.similarity) as avg_similarity
                """
            )
            record = result.single()
            if record:
                return {
                    'num_courses': record['num_courses'],
                    'num_similarity_edges': record['num_similarity_edges'],
                    'num_identical_edges': record['num_identical_edges'],
                    'avg_similarity': round(record['avg_similarity'] or 0, 4)
                }
            return {
                'num_courses': 0,
                'num_similarity_edges': 0,
                'num_identical_edges': 0,
                'avg_similarity': 0
            }
    
    @staticmethod
    def check_connection() -> bool:
        """Neo4j 연결 상태 확인"""
        try:
            driver = get_neo4j_driver()
            driver.verify_connectivity()
            return True
        except Exception:
            return False
    
    # ==================== 교과목 검색 ====================
    
    @staticmethod
    def search_courses(keyword: str, category: Optional[str] = None, 
                       department: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        키워드로 교과목 검색
        
        Args:
            keyword: 검색 키워드
            category: 이수구분 필터 (선택)
            department: 학과 필터 (선택)
            limit: 결과 제한 개수
        """
        with get_session() as session:
            # 동적 필터 구성
            filters = ["(c.name CONTAINS $keyword OR c.description CONTAINS $keyword)"]
            params = {"keyword": keyword, "limit": limit}
            
            if category:
                filters.append("c.category = $category")
                params["category"] = category
            
            if department:
                filters.append("c.department CONTAINS $department")
                params["department"] = department
            
            where_clause = " AND ".join(filters)
            
            result = session.run(
                f"""
                MATCH (c:Course)
                WHERE {where_clause}
                OPTIONAL MATCH (c)-[r:SIMILAR_TO]-()
                WITH c, count(r) as connections
                RETURN c.id as id,
                       c.code as code,
                       c.name as name,
                       c.category as category,
                       c.department as department,
                       c.credits as credits,
                       c.description as description,
                       connections
                ORDER BY connections DESC, c.name
                LIMIT $limit
                """,
                **params
            )
            return [dict(record) for record in result]
    
    @staticmethod
    def get_course_by_code(code: str) -> Optional[Dict]:
        """학수번호로 교과목 조회"""
        with get_session() as session:
            result = session.run(
                """
                MATCH (c:Course {code: $code})
                OPTIONAL MATCH (c)-[r:SIMILAR_TO]-()
                WITH c, count(r) as connections
                RETURN c.id as id,
                       c.code as code,
                       c.name as name,
                       c.category as category,
                       c.department as department,
                       c.credits as credits,
                       c.description as description,
                       c.summary as summary,
                       connections
                LIMIT 1
                """,
                code=code
            )
            record = result.single()
            return dict(record) if record else None
    
    @staticmethod
    def get_course_by_name(name: str) -> Optional[Dict]:
        """교과목 이름으로 조회"""
        with get_session() as session:
            result = session.run(
                """
                MATCH (c:Course {name: $name})
                OPTIONAL MATCH (c)-[r:SIMILAR_TO]-()
                WITH c, count(r) as connections
                RETURN c.id as id,
                       c.code as code,
                       c.name as name,
                       c.category as category,
                       c.department as department,
                       c.credits as credits,
                       c.description as description,
                       c.summary as summary,
                       connections
                LIMIT 1
                """,
                name=name
            )
            record = result.single()
            return dict(record) if record else None
    
    # ==================== 유사 교과목 추천 ====================
    
    @staticmethod
    def get_similar_courses(course_name: str, top_k: int = 10, 
                            min_similarity: float = 0.5) -> List[Dict]:
        """
        특정 교과목과 유사한 교과목 추천
        
        Args:
            course_name: 기준 교과목 이름
            top_k: 추천 개수
            min_similarity: 최소 유사도
        """
        with get_session() as session:
            result = session.run(
                """
                MATCH (c1:Course {name: $name})-[r:SIMILAR_TO]-(c2:Course)
                WHERE r.similarity >= $min_sim
                WITH DISTINCT c2.name as name,
                     c2.code as code,
                     c2.department as department,
                     c2.category as category,
                     c2.credits as credits,
                     c2.description as description,
                     max(r.similarity) as similarity
                RETURN name, code, department, category, credits, description, similarity
                ORDER BY similarity DESC
                LIMIT $top_k
                """,
                name=course_name,
                top_k=top_k,
                min_sim=min_similarity
            )
            return [dict(record) for record in result]
    
    @staticmethod
    def get_similar_courses_by_code(course_code: str, top_k: int = 10,
                                     min_similarity: float = 0.5) -> List[Dict]:
        """학수번호로 유사 교과목 추천"""
        with get_session() as session:
            result = session.run(
                """
                MATCH (c1:Course {code: $code})-[r:SIMILAR_TO]-(c2:Course)
                WHERE r.similarity >= $min_sim
                WITH DISTINCT c2.name as name,
                     c2.code as code,
                     c2.department as department,
                     c2.category as category,
                     c2.credits as credits,
                     c2.description as description,
                     max(r.similarity) as similarity
                RETURN name, code, department, category, credits, description, similarity
                ORDER BY similarity DESC
                LIMIT $top_k
                """,
                code=course_code,
                top_k=top_k,
                min_sim=min_similarity
            )
            return [dict(record) for record in result]
    
    @staticmethod
    def recommend_by_multiple_courses(taken_courses: List[str], 
                                       top_k: int = 10) -> List[Dict]:
        """
        여러 교과목을 수강한 학생에게 다음 교과목 추천
        
        Args:
            taken_courses: 이미 수강한 교과목 이름 리스트
            top_k: 추천 개수
        """
        with get_session() as session:
            result = session.run(
                """
                MATCH (taken:Course)-[r:SIMILAR_TO]-(recommended:Course)
                WHERE taken.name IN $taken_courses
                  AND NOT recommended.name IN $taken_courses
                WITH recommended, 
                     avg(r.similarity) as avg_similarity, 
                     count(*) as common_connections
                RETURN recommended.name as name,
                       recommended.code as code,
                       recommended.category as category,
                       recommended.department as department,
                       recommended.credits as credits,
                       recommended.description as description,
                       avg_similarity,
                       common_connections
                ORDER BY avg_similarity DESC, common_connections DESC
                LIMIT $top_k
                """,
                taken_courses=taken_courses,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    # ==================== 그래프 분석 ====================
    
    @staticmethod
    def get_degree_centrality(top_k: int = 20) -> List[Dict]:
        """
        연결 중심성 분석 - 가장 많은 교과목과 연결된 교과목
        """
        with get_session() as session:
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
    
    @staticmethod
    def get_course_communities(similarity_threshold: float = 0.7,
                                min_cluster_size: int = 3) -> List[Dict]:
        """
        유사도 기반 교과목 커뮤니티(클러스터) 탐지
        """
        with get_session() as session:
            result = session.run(
                """
                MATCH (c1:Course)-[r:SIMILAR_TO]-(c2:Course)
                WHERE r.similarity >= $threshold
                WITH c1, collect(DISTINCT c2.name) as similar_courses, 
                     count(DISTINCT c2) as cluster_size
                WHERE cluster_size >= $min_size
                RETURN c1.name as course_name,
                       c1.code as code,
                       c1.department as department,
                       similar_courses,
                       cluster_size
                ORDER BY cluster_size DESC
                """,
                threshold=similarity_threshold,
                min_size=min_cluster_size
            )
            return [dict(record) for record in result]
    
    @staticmethod
    def get_course_path(start_course: str, end_course: str, 
                        max_hops: int = 3) -> Optional[Dict]:
        """
        두 교과목 간의 유사도 경로 찾기
        """
        with get_session() as session:
            # max_hops를 쿼리에 직접 삽입 (파라미터화 불가)
            result = session.run(
                f"""
                MATCH path = shortestPath(
                    (start:Course {{name: $start}})-[:SIMILAR_TO*..{max_hops}]-(end:Course {{name: $end}})
                )
                RETURN [node in nodes(path) | node.name] as course_path,
                       [rel in relationships(path) | rel.similarity] as similarities,
                       length(path) as path_length
                """,
                start=start_course,
                end=end_course
            )
            record = result.single()
            return dict(record) if record else None
    
    # ==================== 학수번호 기반 분석 ====================
    
    @staticmethod
    def get_identical_id_courses(course_name: str) -> List[Dict]:
        """
        동일한 학수번호를 가진 다른 학과의 교과목 찾기
        """
        with get_session() as session:
            result = session.run(
                """
                MATCH (c1:Course {name: $name})-[r:IDENTICAL_ID]-(c2:Course)
                RETURN c2.name as name,
                       c2.code as code,
                       c2.department as department,
                       c1.department as original_department,
                       c2.category as category,
                       r.note as note
                ORDER BY c2.department
                """,
                name=course_name
            )
            return [dict(record) for record in result]
    
    @staticmethod
    def get_shared_course_ids(top_k: int = 20) -> List[Dict]:
        """
        여러 학과에서 공유하는 학수번호 통계
        """
        with get_session() as session:
            result = session.run(
                """
                MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
                WITH c.code as course_code,
                     c.name as course_name,
                     collect(DISTINCT c.department) + collect(DISTINCT c2.department) as departments
                WITH course_code, course_name, departments, size(departments) as dept_count
                WHERE dept_count > 1
                RETURN course_code,
                       course_name,
                       departments,
                       dept_count
                ORDER BY dept_count DESC
                LIMIT $top_k
                """,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    # ==================== 교과과정 분석 ====================
    
    @staticmethod
    def get_curriculum_structure(department: Optional[str] = None) -> Dict:
        """
        교과과정 구조 분석
        
        Args:
            department: 분석할 학과 (None이면 전체)
        """
        with get_session() as session:
            # 부서 필터
            dept_filter = "WHERE c.department CONTAINS $dept" if department else ""
            dept_param = department or ""
            
            # 이수구분별 통계
            cat_result = session.run(
                f"""
                MATCH (c:Course)
                {dept_filter}
                WITH c.category as category, 
                     count(*) as course_count,
                     avg(c.credits) as avg_credits
                RETURN category, course_count, avg_credits
                ORDER BY course_count DESC
                """,
                dept=dept_param
            )
            categories = [dict(record) for record in cat_result]
            
            # 전체 통계
            total_result = session.run(
                f"""
                MATCH (c:Course)
                {dept_filter}
                RETURN count(*) as total_courses,
                       sum(c.credits) as total_credits,
                       avg(c.credits) as avg_credits
                """,
                dept=dept_param
            )
            total_stats = total_result.single()
            
            return {
                'department': department or '전체',
                'total_courses': total_stats['total_courses'] if total_stats else 0,
                'total_credits': total_stats['total_credits'] if total_stats else 0,
                'avg_credits': round(total_stats['avg_credits'] or 0, 2) if total_stats else 0,
                'categories': categories
            }
    
    @staticmethod
    def get_departments() -> List[str]:
        """모든 학과 목록 조회"""
        with get_session() as session:
            result = session.run(
                """
                MATCH (c:Course)
                WHERE c.department IS NOT NULL AND c.department <> ''
                RETURN DISTINCT c.department as department
                ORDER BY department
                """
            )
            return [record['department'] for record in result]
    
    @staticmethod
    def get_categories() -> List[str]:
        """모든 이수구분 목록 조회"""
        with get_session() as session:
            result = session.run(
                """
                MATCH (c:Course)
                WHERE c.category IS NOT NULL AND c.category <> ''
                RETURN DISTINCT c.category as category
                ORDER BY category
                """
            )
            return [record['category'] for record in result]
    
    # ==================== 학과별 추천 ====================
    
    @staticmethod
    def recommend_by_department(department: str, 
                                 taken_courses: Optional[List[str]] = None,
                                 top_k: int = 10) -> List[Dict]:
        """
        특정 학과의 교과목 중 추천
        """
        taken_courses = taken_courses or []
        
        with get_session() as session:
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
                       c.department as department,
                       c.description as description,
                       avg_connectivity,
                       connections
                ORDER BY connections DESC, avg_connectivity DESC
                LIMIT $top_k
                """,
                dept=department,
                taken=taken_courses,
                top_k=top_k
            )
            return [dict(record) for record in result]
    
    # ==================== 유사도 조회 ====================
    
    @staticmethod
    def get_similarity_between(code1: str, code2: str) -> float:
        """
        두 과목 간 유사도 조회
        
        Args:
            code1: 첫 번째 과목 학수번호
            code2: 두 번째 과목 학수번호
            
        Returns:
            유사도 (0.0 ~ 1.0), 관계 없으면 0.0
        """
        with get_session() as session:
            result = session.run(
                """
                MATCH (c1:Course {code: $code1})-[r:SIMILAR_TO]-(c2:Course {code: $code2})
                RETURN r.similarity as similarity
                LIMIT 1
                """,
                code1=code1,
                code2=code2
            )
            record = result.single()
            return float(record['similarity']) if record else 0.0