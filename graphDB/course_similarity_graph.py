"""
교과목 유사도 기반 그래프 네트워크 구축
Neo4j GraphRAG Python 패키지 사용
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from neo4j import GraphDatabase
import os
from typing import List, Tuple
import warnings
warnings.filterwarnings('ignore')


class CourseGraphBuilder:
    """교과목 그래프 네트워크 구축 클래스"""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", 
                 neo4j_password: str = "password"):
        """
        Args:
            neo4j_uri: Neo4j 데이터베이스 URI
            neo4j_user: Neo4j 사용자명
            neo4j_password: Neo4j 비밀번호
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        print(f"임베딩 모델 로드 완료: jhgan/ko-sroberta-multitask")
        
    def close(self):
        """데이터베이스 연결 종료"""
        self.driver.close()
        
    def load_course_data(self, csv_path: str) -> pd.DataFrame:
        """
        교과목 데이터 로드
        
        Args:
            csv_path: CSV 파일 경로
            
        Returns:
            교과목 데이터프레임
        """
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # feature_text 컬럼 생성: 교과목 이름 + 교과목개요 결합 (GraphRAG용)
        df['feature_text'] = df['교과목 이름'] + " " + df['교과목개요'].fillna("")
        
        # 동일 학수번호/다른 학과 체크용 분석
        id_counts = df.groupby('학수번호')['설강학과'].nunique()
        shared_ids = id_counts[id_counts > 1].index.tolist()
        print(f"데이터 로드 완료: {len(df)} 개 교과목")
        print(f"여러 학과에서 공유하는 학수번호 개수: {len(shared_ids)}")
        
        return df
    
    def create_embeddings(self, df: pd.DataFrame) -> np.ndarray:
        """
        교과목 텍스트를 임베딩 벡터로 변환
        feature_text (교과목 이름 + 교과목개요)를 기반으로 임베딩 생성
        
        Args:
            df: 교과목 데이터프레임 (feature_text 컬럼 필요)
            
        Returns:
            임베딩 벡터 배열 (n_courses, embedding_dim)
        """
        # feature_text 사용 (교과목 이름 + 교과목개요)
        texts = df['feature_text'].tolist()
        
        print(f"임베딩 생성 중... (feature_text 사용: 교과목 이름 + 개요)")
        embeddings = self.embedding_model.encode(texts, 
                                                 batch_size=32,
                                                 show_progress_bar=True,
                                                 convert_to_numpy=True)
        print(f"임베딩 생성 완료: shape = {embeddings.shape}")
        return embeddings
    
    def compute_similarity(self, df: pd.DataFrame, embeddings: np.ndarray, 
                          threshold: float = 0.7) -> List[Tuple[int, int, float]]:
        """
        코사인 유사도 계산 및 엣지 생성
        같은 학수번호를 가진 교과목끼리는 엣지를 생성하지 않음
        
        Args:
            df: 교과목 데이터프레임 (학수번호 확인용)
            embeddings: 임베딩 벡터 배열
            threshold: 유사도 임계값 (이 값 이상인 경우만 엣지 생성)
            
        Returns:
            (course_i, course_j, similarity) 튜플 리스트
        """
        print(f"유사도 계산 중... (임계값: {threshold})")
        similarity_matrix = cosine_similarity(embeddings)
        
        # 학수번호 리스트
        course_codes = df['학수번호'].tolist()
        
        edges = []
        same_code_skipped = 0
        n = len(similarity_matrix)
        
        for i in range(n):
            for j in range(i+1, n):  # 상삼각 행렬만 확인 (중복 방지)
                # 같은 학수번호면 스킵
                if course_codes[i] == course_codes[j]:
                    same_code_skipped += 1
                    continue
                
                sim = similarity_matrix[i][j]
                if sim >= threshold:
                    edges.append((i, j, float(sim)))
        
        print(f"생성된 엣지 수: {len(edges)}")
        print(f"같은 학수번호로 스킵된 쌍: {same_code_skipped}")
        return edges
    
    def compute_identical_id_edges(self, df: pd.DataFrame) -> List[Tuple[int, int, str, str]]:
        """
        학수번호는 동일하나 설강학과가 다른 교과목 쌍 찾기
        
        Args:
            df: 교과목 데이터프레임
            
        Returns:
            (course_i, course_j, dept_i, dept_j) 튜플 리스트
        """
        print("학수번호 기반 엣지 계산 중...")
        
        edges = []
        course_codes = df['학수번호'].tolist()
        departments = df['설강학과'].tolist()
        
        # 학수번호로 그룹핑
        code_to_indices = {}
        for idx, code in enumerate(course_codes):
            if code not in code_to_indices:
                code_to_indices[code] = []
            code_to_indices[code].append(idx)
        
        # 같은 학수번호, 다른 학과인 쌍 생성
        for code, indices in code_to_indices.items():
            if len(indices) > 1:
                for i in range(len(indices)):
                    for j in range(i+1, len(indices)):
                        idx_i, idx_j = indices[i], indices[j]
                        dept_i, dept_j = departments[idx_i], departments[idx_j]
                        
                        # 설강학과가 다른 경우만 추가
                        if dept_i != dept_j:
                            edges.append((idx_i, idx_j, dept_i, dept_j))
        
        print(f"학수번호 기반 엣지 수: {len(edges)}")
        return edges
    
    def clear_database(self):
        """기존 그래프 데이터 삭제"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("기존 데이터베이스 초기화 완료")
    
    def create_graph(self, df: pd.DataFrame, edges: List[Tuple[int, int, float]], 
                    identical_edges: List[Tuple[int, int, str, str]] = None):
        """
        Neo4j 그래프 생성
        
        Args:
            df: 교과목 데이터프레임
            edges: 유사도 기반 엣지 리스트 (course_i, course_j, similarity)
            identical_edges: 학수번호 기반 엣지 리스트 (course_i, course_j, dept_i, dept_j)
        """
        print("그래프 생성 중...")
        
        with self.driver.session() as session:
            # 1. 노드 생성 (교과목)
            print("  - 노드 생성 중...")
            for idx, row in df.iterrows():
                # 컬럼 존재 여부 확인 후 안전하게 접근
                credits = 0
                if '학점' in df.columns and pd.notna(row.get('학점')):
                    credits = int(row['학점'])
                elif '학년' in df.columns and pd.notna(row.get('학년')):
                    credits = int(row['학년'])  # 학년을 임시로 사용
                
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
                        summary: $summary
                    })
                    """,
                    id=int(idx),
                    code=row['학수번호'],
                    name=row['교과목 이름'],
                    credits=credits,
                    category=row['이수구분'] if pd.notna(row['이수구분']) else '',
                    department=row['설강학과'] if pd.notna(row['설강학과']) else '',
                    description=row['교과목개요'] if pd.notna(row['교과목개요']) else '',
                    summary=row.get('교과목개요_요약', '') if pd.notna(row.get('교과목개요_요약')) else ''
                )
            
            # 2. 엣지 생성 (유사도 관계)
            print("  - 유사도 엣지 생성 중...")
            batch_size = 1000
            for i in range(0, len(edges), batch_size):
                batch = edges[i:i+batch_size]
                session.run(
                    """
                    UNWIND $edges AS edge
                    MATCH (c1:Course {id: edge.source})
                    MATCH (c2:Course {id: edge.target})
                    CREATE (c1)-[:SIMILAR_TO {similarity: edge.weight}]->(c2)
                    """,
                    edges=[
                        {'source': e[0], 'target': e[1], 'weight': e[2]}
                        for e in batch
                    ]
                )
                print(f"    진행: {min(i+batch_size, len(edges))}/{len(edges)} 엣지")
            
            # 3. 학수번호 기반 엣지 생성 (IDENTICAL_ID 관계)
            if identical_edges:
                print("  - 학수번호 기반 엣지 생성 중...")
                for i in range(0, len(identical_edges), batch_size):
                    batch = identical_edges[i:i+batch_size]
                    session.run(
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
                        edges=[
                            {'source': e[0], 'target': e[1], 'dept1': e[2], 'dept2': e[3]}
                            for e in batch
                        ]
                    )
                    print(f"    진행: {min(i+batch_size, len(identical_edges))}/{len(identical_edges)} 엣지")
        
        print("그래프 생성 완료!")
    
    def create_indexes(self):
        """인덱스 생성으로 쿼리 성능 향상"""
        with self.driver.session() as session:
            session.run("CREATE INDEX course_id IF NOT EXISTS FOR (c:Course) ON (c.id)")
            session.run("CREATE INDEX course_code IF NOT EXISTS FOR (c:Course) ON (c.code)")
            session.run("CREATE INDEX course_name IF NOT EXISTS FOR (c:Course) ON (c.name)")
        print("인덱스 생성 완료")
    
    def get_statistics(self) -> dict:
        """그래프 통계 조회"""
        with self.driver.session() as session:
            result = session.run(
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
            )
            stats = result.single()
            return {
                'num_courses': stats['num_courses'],
                'num_edges': stats['num_edges'] // 2,  # 양방향이므로 2로 나눔
                'avg_similarity': stats['avg_similarity'],
                'max_similarity': stats['max_similarity'],
                'min_similarity': stats['min_similarity']
            }
    
    def find_similar_courses(self, course_name: str, top_k: int = 10) -> List[dict]:
        """
        특정 교과목과 유사한 교과목 찾기
        
        Args:
            course_name: 교과목 이름
            top_k: 상위 k개 반환
            
        Returns:
            유사 교과목 리스트
        """
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
                top_k=top_k
            )
            return [dict(record) for record in result]


def main():
    """메인 실행 함수"""
    
    # 설정
    CSV_PATH = "C:/Users/PC/course_graph_neo4j/final_course.csv"
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "your_password"  # 실제 비밀번호로 변경 필요
    SIMILARITY_THRESHOLD = 0.5  # 유사도 임계값
    
    # 그래프 빌더 초기화
    print("=" * 80)
    print("교과목 유사도 그래프 네트워크 구축")
    print("=" * 80)
    
    builder = CourseGraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # 1. 데이터 로드
        print("\n[1단계] 데이터 로드")
        df = builder.load_course_data(CSV_PATH)
        
        # 2. 임베딩 생성
        print("\n[2단계] 임베딩 생성")
        embeddings = builder.create_embeddings(df)
        
        # 3. 유사도 계산
        print("\n[3단계] 유사도 계산")
        edges = builder.compute_similarity(df, embeddings, threshold=SIMILARITY_THRESHOLD)
        
        # 3-2. 학수번호 기반 관계 계산
        print("\n[3-2단계] 학수번호 기반 관계 계산")
        identical_edges = builder.compute_identical_id_edges(df)
        
        # 4. 기존 데이터 삭제 (선택사항)
        print("\n[4단계] 데이터베이스 초기화")
        # builder.clear_database()  # 주석 해제하여 사용
        
        # 5. 그래프 생성
        print("\n[5단계] Neo4j 그래프 생성")
        builder.create_graph(df, edges, identical_edges)
        
        # 6. 인덱스 생성
        print("\n[6단계] 인덱스 생성")
        builder.create_indexes()
        
        # 7. 통계 확인
        print("\n[7단계] 그래프 통계")
        stats = builder.get_statistics()
        print(f"  - 교과목 수: {stats['num_courses']}")
        print(f"  - 엣지 수: {stats['num_edges']}")
        print(f"  - 평균 유사도: {stats['avg_similarity']:.4f}")
        print(f"  - 최대 유사도: {stats['max_similarity']:.4f}")
        print(f"  - 최소 유사도: {stats['min_similarity']:.4f}")
        
        # 8. 예시: 유사 교과목 검색
        print("\n[8단계] 예시: 유사 교과목 검색")
        example_course = df.iloc[0]['교과목 이름']
        print(f"검색 교과목: {example_course}")
        similar = builder.find_similar_courses(example_course, top_k=5)
        for i, course in enumerate(similar, 1):
            print(f"  {i}. {course['name']} ({course['code']}) - 유사도: {course['similarity']:.4f}")
        
        print("\n" + "=" * 80)
        print("그래프 구축 완료!")
        print("=" * 80)
        
    finally:
        builder.close()


if __name__ == "__main__":
    main()