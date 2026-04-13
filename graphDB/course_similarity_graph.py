"""
교과목 유사도 기반 그래프 네트워크 구축
Neo4j GraphRAG Python 패키지 사용
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
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
        # 다국어 모델 (영어+한국어 혼합 데이터에 적합)
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self._tfidf_vectors = None  # TF-IDF 하이브리드용
        self._hybrid_weight = 0.7   # 임베딩 가중치 (기본 70%)
        print(f"임베딩 모델 로드 완료: paraphrase-multilingual-MiniLM-L12-v2 (다국어 지원)")
        
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
        if '학수번호' in df.columns:
            id_counts = df.groupby('학수번호')['설강학과'].nunique()
            shared_ids = id_counts[id_counts > 1].index.tolist()
            print(f"데이터 로드 완료: {len(df)} 개 교과목")
            print(f"여러 학과에서 공유하는 학수번호 개수: {len(shared_ids)}")
        else:
            print(f"데이터 로드 완료: {len(df)} 개 교과목")
            print("학수번호 컬럼이 없어 공유 과목 분석을 생략합니다.")
        
        return df
    
    def create_embeddings(self, df: pd.DataFrame, use_tfidf_weighting: bool = True) -> np.ndarray:
        """
        교과목 텍스트를 임베딩 벡터로 변환
        TF-IDF 가중치를 적용하여 상투적 표현의 영향을 감소시킴
        
        Args:
            df: 교과목 데이터프레임 (feature_text 컬럼 필요)
            use_tfidf_weighting: TF-IDF 하이브리드 방식 적용 여부 (기본: True)
            
        Returns:
            임베딩 벡터 배열 (n_courses, embedding_dim)
        """
        # 교과목 이름 + 교과목개요 사용 (사용자 요청 사항)
        texts = df['feature_text'].tolist()
        
        # 상투적 표현 제거
        stopwords = {
            '대한', '통해', '여러', '다양한', '되는', '이해하고', '있는', '한다',
            '등을', '개념을', '위한', '능력을', '있도록', '이를', '있다', '위해',
            '이해를', '배우고', '학습한다', '익힌다', '다룬다', '강의한다',
            '수업은', '과목은', '본', '및', '등', '수', '것', '더', '또한',
            '대해', '관한', '하는', '되어', '같은', '따른', '따라', '관련',
            '기반으로', '목표로', '중심으로', '통하여', '바탕으로',
            '이', '그', '저', '것', '수', '등', '및', '또', '더', '매우',
        }
        
        texts_filtered = [
            ' '.join([w for w in t.split() if w not in stopwords and len(w) > 1])
            for t in texts
        ]
        
        print(f"임베딩 생성 중... (상투적 표현 {len(stopwords)}개 제거)")
        embeddings = self.embedding_model.encode(
            texts_filtered,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        if use_tfidf_weighting:
            print(f"TF-IDF 하이브리드 적용 중... (임베딩 70% + TF-IDF 30%)")
            embeddings = self._apply_tfidf_hybrid(texts, embeddings)
        
        print(f"임베딩 생성 완료: shape = {embeddings.shape}")
        return embeddings
    
    def _apply_tfidf_hybrid(self, texts: List[str], embeddings: np.ndarray) -> np.ndarray:
        """
        임베딩과 TF-IDF 벡터를 조합한 하이브리드 유사도용 벡터 생성
        - 임베딩: 의미적 유사도 (70%)
        - TF-IDF: 키워드 기반 유사도 (30%)
        
        Args:
            texts: 원본 텍스트 리스트
            embeddings: SBERT 임베딩
            
        Returns:
            하이브리드 임베딩 벡터
        """
        # TF-IDF 벡터 생성
        tfidf = TfidfVectorizer(
            max_features=3000,
            min_df=2,
            max_df=0.7,  # 70% 이상 문서에 등장하면 제외 (상투적 표현)
            sublinear_tf=True,
            ngram_range=(1, 2),
        )
        tfidf_matrix = tfidf.fit_transform(texts)
        tfidf_dense = tfidf_matrix.toarray()
        
        print(f"  - TF-IDF 어휘 크기: {len(tfidf.get_feature_names_out())}")
        
        # 정규화
        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        tfidf_norm = tfidf_dense / (np.linalg.norm(tfidf_dense, axis=1, keepdims=True) + 1e-8)
        
        # TF-IDF를 임베딩 차원으로 변환 (PCA나 간단한 선형 변환)
        # 여기서는 TF-IDF를 유사도 계산에만 사용하고, 
        # 실제 저장되는 임베딩은 SBERT 임베딩 유지
        # 유사도 계산 시 하이브리드로 조합
        
        # 메타데이터로 TF-IDF 정보 저장 (나중에 compute_similarity 및 선수강 매핑에서 사용)
        self._tfidf_vectorizer = tfidf
        self._tfidf_vectors = tfidf_norm
        self._hybrid_weight = 0.7  # 임베딩 가중치
        
        return emb_norm
    
    def _is_sequential_course(self, name1: str, name2: str) -> bool:
        """
        두 과목이 연계 과목(1, 2 시리즈)인지 확인
        예: 미분적분학1 vs 미분적분학2, 일반물리학1 vs 일반물리학2
        
        Args:
            name1: 첫 번째 과목명
            name2: 두 번째 과목명
            
        Returns:
            연계 과목이면 True
        """
        import re
        
        # 숫자를 제거한 기본 이름 추출
        def get_base_name(name):
            # 끝에 붙은 숫자 제거 (1, 2, I, II 등)
            base = re.sub(r'[0-9IⅠⅡ]+$', '', name.strip())
            # 괄호 안 내용도 제거
            base = re.sub(r'\([^)]*\)$', '', base.strip())
            return base.strip()
        
        # 끝에 붙은 숫자/로마자 추출
        def get_sequence_num(name):
            match = re.search(r'([0-9IⅠⅡ]+)$', name.strip())
            if match:
                num = match.group(1)
                # 로마 숫자 변환
                num = num.replace('Ⅰ', '1').replace('Ⅱ', '2').replace('I', '1').replace('II', '2')
                return num
            return None
        
        base1 = get_base_name(name1)
        base2 = get_base_name(name2)
        seq1 = get_sequence_num(name1)
        seq2 = get_sequence_num(name2)
        
        # 기본 이름이 같고, 둘 다 시퀀스 번호가 있고, 번호가 다르면 연계 과목
        if base1 == base2 and seq1 and seq2 and seq1 != seq2:
            return True
        
        return False
    
    def compute_prerequisite_edges(self, df: pd.DataFrame, course_embeddings: np.ndarray, threshold: float = 0.7) -> Tuple[List[Tuple[int, int, float, str]], dict]:
        """
        선수강과목 매핑 연산
        
        Returns:
            prereq_edges: [(source_idx, target_idx, sim, raw_text), ...]
            unmapped: {course_idx: [unmapped_texts...]}
        """
        print(f"선수강과목 파싱 및 매핑 중... (임계값: {threshold})")
        
        prereq_edges = []
        unmapped = {}
        
        course_names_raw = df['교과목 이름'].tolist()
        course_names_clean = [str(n).strip().replace(" ", "").lower() for n in course_names_raw]
        name_to_idx = {name: idx for idx, name in enumerate(course_names_clean)}
        
        stopwords = {
            '대한', '통해', '여러', '다양한', '되는', '이해하고', '있는', '한다',
            '등을', '개념을', '위한', '능력을', '있도록', '이를', '있다', '위해',
            '이해를', '배우고', '학습한다', '익힌다', '다룬다', '강의한다',
            '수업은', '과목은', '본', '및', '등', '수', '것', '더', '또한',
            '대해', '관한', '하는', '되어', '같은', '따른', '따라', '관련',
            '기반으로', '목표로', '중심으로', '통하여', '바탕으로',
            '이', '그', '저', '매우', '수강하셨으면', '필수', '요구', 
            '요구됨', '필요', '필요함', '필요합니다', '수강', '선수강', '추천', '좋습니다', '아닙니다'
        }
        
        exact_match_count = 0
        semantic_match_count = 0
        unmapped_count = 0
        
        col_name = '선수강 과목' if '선수강 과목' in df.columns else '선수강과목'
        if col_name not in df.columns:
            print("선수강과목 컬럼을 찾을 수 없습니다.")
            return [], {}
            
        for idx, row in df.iterrows():
            prereq_text = row.get(col_name)
            if pd.isna(prereq_text) or str(prereq_text).strip() == "":
                continue
                
            raw_items = [item.strip() for item in str(prereq_text).split(',')]
            unmapped_for_this_course = []
            
            for item in raw_items:
                if not item: continue
                clean_item = item.replace(" ", "").lower()
                
                # 1. Exact Match 시도
                if clean_item in name_to_idx:
                    target_idx = name_to_idx[clean_item]
                    prereq_edges.append((idx, target_idx, 1.0, item))
                    exact_match_count += 1
                    continue
                    
                # 2. Semantic Match (임베딩 하이브리드)
                filtered_item = ' '.join([w for w in item.split() if w not in stopwords and len(w) > 1])
                if not filtered_item:
                    unmapped_for_this_course.append(item)
                    unmapped_count += 1
                    continue
                    
                item_emb = self.embedding_model.encode([filtered_item], convert_to_numpy=True)
                item_emb_norm = item_emb / (np.linalg.norm(item_emb, axis=1, keepdims=True) + 1e-8)
                sim_embedding = cosine_similarity(item_emb_norm, course_embeddings)[0]
                
                if hasattr(self, '_tfidf_vectorizer') and self._tfidf_vectors is not None:
                    item_tfidf = self._tfidf_vectorizer.transform([filtered_item]).toarray()
                    item_tfidf_norm = item_tfidf / (np.linalg.norm(item_tfidf, axis=1, keepdims=True) + 1e-8)
                    sim_tfidf = cosine_similarity(item_tfidf_norm, self._tfidf_vectors)[0]
                    
                    weight = getattr(self, '_hybrid_weight', 0.7)
                    sim_final = weight * sim_embedding + (1 - weight) * sim_tfidf
                else:
                    sim_final = sim_embedding
                
                best_idx = np.argmax(sim_final)
                best_score = sim_final[best_idx]
                
                if best_score >= threshold:
                    prereq_edges.append((idx, int(best_idx), float(best_score), item))
                    semantic_match_count += 1
                else:
                    unmapped_for_this_course.append(item)
                    unmapped_count += 1
                    
            if unmapped_for_this_course:
                unmapped[idx] = unmapped_for_this_course
                
        print(f"선수강과목 매핑 완료:")
        print(f"  - 정확히 일치 (Exact Match): {exact_match_count} 건")
        print(f"  - 유사도 일치 (Semantic Match >= {threshold}): {semantic_match_count} 건")
        print(f"  - 매핑 실패 (Unmapped): {unmapped_count} 건")
        
        return prereq_edges, unmapped
    
    def compute_similarity(self, df: pd.DataFrame, embeddings: np.ndarray, 
                          threshold: float = 0.7) -> List[Tuple[int, int, float]]:
        """
        코사인 유사도 계산 및 엣지 생성
        - 같은 학수번호를 가진 교과목끼리는 엣지를 생성하지 않음
        - 연계 과목 (1, 2 시리즈)끼리는 엣지를 생성하지 않음
        
        Args:
            df: 교과목 데이터프레임 (학수번호 확인용)
            embeddings: 임베딩 벡터 배열
            threshold: 유사도 임계값 (이 값 이상인 경우만 엣지 생성)
            
        Returns:
            (course_i, course_j, similarity) 튜플 리스트
        """
        print(f"유사도 계산 중... (임계값: {threshold})")
        
        # 임베딩 기반 유사도
        sim_embedding = cosine_similarity(embeddings)
        
        # TF-IDF 하이브리드 적용 여부 확인
        if hasattr(self, '_tfidf_vectors') and self._tfidf_vectors is not None:
            sim_tfidf = cosine_similarity(self._tfidf_vectors)
            weight = self._hybrid_weight
            similarity_matrix = weight * sim_embedding + (1 - weight) * sim_tfidf
            print(f"  - 하이브리드 유사도 적용: 임베딩 {weight*100:.0f}% + TF-IDF {(1-weight)*100:.0f}%")
        else:
            similarity_matrix = sim_embedding
        
        # 학수번호, 과목명 리스트
        course_codes = df['학수번호'].tolist() if '학수번호' in df.columns else [''] * len(df)
        course_names = df['교과목 이름'].tolist()
        
        edges = []
        same_code_skipped = 0
        sequential_skipped = 0
        n = len(similarity_matrix)
        
        for i in range(n):
            for j in range(i+1, n):  # 상삼각 행렬만 확인 (중복 방지)
                # 같은 학수번호면 스킵
                if course_codes[i] and course_codes[i] == course_codes[j]:
                    same_code_skipped += 1
                    continue
                
                # 연계 과목 (1, 2 시리즈)이면 스킵
                if self._is_sequential_course(course_names[i], course_names[j]):
                    sequential_skipped += 1
                    continue
                
                sim = similarity_matrix[i][j]
                if sim >= threshold:
                    edges.append((i, j, float(sim)))
        
        print(f"생성된 엣지 수: {len(edges)}")
        print(f"같은 학수번호로 스킵된 쌍: {same_code_skipped}")
        print(f"연계 과목(1,2 시리즈)으로 스킵된 쌍: {sequential_skipped}")
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
        if '학수번호' not in df.columns:
            print("  - 학수번호 컬럼이 없으므로 계산을 생략합니다.")
            return []
        
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
                    identical_edges: List[Tuple[int, int, str, str]] = None,
                    prereq_edges: List[Tuple[int, int, float, str]] = None,
                    unmapped_prereqs: dict = None):
        """
        Neo4j 그래프 생성
        
        Args:
            df: 교과목 데이터프레임
            edges: 유사도 기반 엣지 리스트 (course_i, course_j, similarity)
            identical_edges: 학수번호 기반 엣지 리스트 (course_i, course_j, dept_i, dept_j)
            prereq_edges: 선수강과목 매핑 엣지 (source, target, sim, raw_text)
            unmapped_prereqs: 매핑 실패한 선수강과목 텍스트 딕셔너리
        """
        print("그래프 생성 중...")
        
        if unmapped_prereqs is None:
            unmapped_prereqs = {}
            
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
                
                unmapped_text = ", ".join(unmapped_prereqs.get(idx, []))
                
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
                    code=row.get('학수번호', ''),
                    name=row['교과목 이름'],
                    credits=credits,
                    category=row['이수구분'] if pd.notna(row['이수구분']) else '',
                    department=row['설강학과'] if pd.notna(row['설강학과']) else '',
                    description=row['교과목개요'] if pd.notna(row['교과목개요']) else '',
                    summary=row.get('교과목개요_요약', '') if pd.notna(row.get('교과목개요_요약')) else '',
                    unmapped_reqs=unmapped_text
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
            
            # 4. 선수강과목 엣지 생성 (REQUIRES 관계)
            if prereq_edges:
                print("  - 선수강과목 엣지 생성 중...")
                for i in range(0, len(prereq_edges), batch_size):
                    batch = prereq_edges[i:i+batch_size]
                    session.run(
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
                        edges=[
                            {'source': e[0], 'target': e[1], 'weight': e[2], 'raw_text': e[3]}
                            for e in batch
                        ]
                    )
                    print(f"    진행: {min(i+batch_size, len(prereq_edges))}/{len(prereq_edges)} 엣지")
                    
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
            # 기본 교과목 및 유사도 엣지 통계
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
            
            # 선수강과목 매핑 엣지 (REQUIRES) 통계
            result_req = session.run("MATCH ()-[r:REQUIRES]->() RETURN count(r) as num_requires")
            req_stats = result_req.single()
            
            return {
                'num_courses': stats['num_courses'],
                'num_edges': stats['num_edges'] // 2 if stats['num_edges'] else 0,
                'num_requires': req_stats['num_requires'],
                'avg_similarity': stats['avg_similarity'] or 0.0,
                'max_similarity': stats['max_similarity'] or 0.0,
                'min_similarity': stats['min_similarity'] or 0.0
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
    CSV_PATH = "C/Users/mjwoon/Workspace/LionsStudentDashboard/graphDB/course_all_aggregated.csv"
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
        
        # 3-3. 선수강과목 매핑
        print("\n[3-3단계] 선수강과목 기반 관계 변환 (Threshold 0.6)")
        PREREQ_THRESHOLD = 0.6
        prereq_edges, unmapped_prereqs = builder.compute_prerequisite_edges(df, embeddings, threshold=PREREQ_THRESHOLD)
        
        # 4. 기존 데이터 삭제 (선택사항)
        print("\n[4단계] 데이터베이스 초기화")
        # builder.clear_database()  # 주석 해제하여 사용
        
        # 5. 그래프 생성
        print("\n[5단계] Neo4j 그래프 생성")
        builder.create_graph(df, edges, identical_edges, prereq_edges, unmapped_prereqs)
        
        # 6. 인덱스 생성
        print("\n[6단계] 인덱스 생성")
        builder.create_indexes()
        
        # 7. 통계 확인
        print("\n[7단계] 그래프 통계")
        stats = builder.get_statistics()
        print(f"  - 교과목 수: {stats['num_courses']}")
        print(f"  - 유사성 엣지(SIMILAR_TO) 수: {stats['num_edges']}")
        print(f"  - 선수강 엣지(REQUIRES) 수: {stats['num_requires']}")
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