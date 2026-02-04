# 교과목 유사도 기반 그래프 네트워크 프로젝트

Neo4j GraphRAG를 활용한 교과목 간 유사도 네트워크 구축 및 분석 시스템

## 📋 프로젝트 개요

**교과목개요**를 기반으로 교과목 간 유사도를 계산하고, Neo4j 그래프 데이터베이스에 네트워크를 구축하여 다양한 분석과 추천 서비스를 제공합니다.

### 주요 기능
- 🔍 **유사도 기반 교과목 추천**: 특정 교과목과 유사한 과목 추천
- 📊 **교과과정 분석**: 이수구분, 학과별 교과목 구조 분석
- 🎯 **학습 경로 탐색**: 교과목 간 연관성을 통한 최적 학습 경로 제시
- 🔗 **네트워크 분석**: 연결 중심성, 클러스터링 등 그래프 분석

## 🎯 데이터 정보

- **교과목 수**: 854개
- **고유 학수번호**: 423개
- **임베딩 기반**: 교과목개요 (평균 258자)
- **유사도 척도**: 코사인 유사도 (Cosine Similarity)

## 🛠️ 기술 스택

- **그래프 DB**: Neo4j 5.x
- **임베딩 모델**: Sentence-BERT (jhgan/ko-sroberta-multitask)
- **언어**: Python 3.8+
- **주요 라이브러리**: 
  - neo4j-driver
  - sentence-transformers
  - pandas, numpy
  - scikit-learn

## 📦 설치 방법

### 1. 필수 요구사항

```bash
# Python 3.8 이상
python --version

# Neo4j 설치 (Docker 권장)
docker --version
```

### 2. Neo4j 실행

```bash
# Docker로 Neo4j 실행
docker run -d \
    --name neo4j-course-graph \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    neo4j:latest

# 브라우저에서 확인: http://localhost:7474
```

### 3. Python 패키지 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

## 🚀 빠른 시작

### 방법 1: 간단한 실행 스크립트

```bash
# quick_start.py 실행
python quick_start.py
```

이 스크립트는 다음 작업을 자동으로 수행합니다:
1. 교과목 데이터 로드
2. 임베딩 생성 (교과목개요 기반)
3. 유사도 계산 및 그래프 생성
4. 샘플 분석 실행

### 방법 2: 단계별 실행

```python
from course_similarity_graph import CourseGraphBuilder

# 1. 그래프 빌더 초기화
builder = CourseGraphBuilder(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="your_password"
)

# 2. 데이터 로드 및 임베딩 생성
df = builder.load_course_data('final_course.csv')
embeddings = builder.create_embeddings(df)  # 교과목개요 기반

# 3. 유사도 계산 (임계값 0.5)
edges = builder.compute_similarity(embeddings, threshold=0.5)

# 4. 그래프 생성
builder.create_graph(df, edges)
builder.create_indexes()

# 5. 통계 확인
stats = builder.get_statistics()
print(stats)
```

### 방법 3: CLI 사용

```bash
# 그래프 구축
python run_course_graph.py --password your_password \
  build --csv-path final_course.csv --threshold 0.5

# 분석 실행
python run_course_graph.py --password your_password \
  analyze --type centrality

python run_course_graph.py --password your_password \
  analyze --type similar --course-name "데이터베이스"
```

## 📊 테스트 및 분석

Neo4j 없이도 데이터 분석과 유사도 계산을 테스트할 수 있습니다:

```bash
# 데이터 분석 및 샘플 유사도 테스트
python test_similarity.py
```

이 스크립트는 다음을 제공합니다:
- 교과목 데이터 통계
- 샘플 교과목 간 유사도 계산
- 임계값별 예상 엣지 수
- 특정 교과목과 유사한 과목 검색

## 💡 사용 예제

### 1. 유사 교과목 추천

```python
from course_graph_analysis import CourseGraphAnalyzer

analyzer = CourseGraphAnalyzer(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="your_password"
)

# 특정 교과목과 유사한 과목 찾기
similar = analyzer.recommend_by_similarity('데이터베이스', top_k=10)
for course in similar:
    print(f"{course['name']} - 유사도: {course['similarity']:.4f}")
```

### 2. 복수 교과목 기반 추천

```python
# 이미 수강한 교과목을 기반으로 다음 과목 추천
taken_courses = ['자료구조', '알고리즘', '운영체제']
recommendations = analyzer.recommend_by_multiple_courses(taken_courses, top_k=10)
```

### 3. 교과과정 분석

```python
# 특정 학과의 교과과정 구조 분석
structure = analyzer.analyze_curriculum_structure('컴퓨터')
print(f"총 교과목: {structure['total_courses']}")
print(f"이수구분별 통계:")
for cat in structure['categories']:
    print(f"  {cat['category']}: {cat['course_count']}과목")
```

### 4. Cypher 쿼리

Neo4j Browser (http://localhost:7474)에서 직접 쿼리 가능:

```cypher
// 가장 유사한 교과목 쌍 찾기
MATCH (c1:Course)-[r:SIMILAR_TO]-(c2:Course)
WHERE c1.id < c2.id
RETURN c1.name, c2.name, r.similarity
ORDER BY r.similarity DESC
LIMIT 10;

// 특정 교과목의 유사 과목 찾기
MATCH (c:Course {name: '데이터베이스'})-[r:SIMILAR_TO]-(other:Course)
RETURN other.name, r.similarity
ORDER BY r.similarity DESC
LIMIT 10;

// 학과별 교과목 네트워크
MATCH (c:Course)
WHERE c.department CONTAINS '컴퓨터'
OPTIONAL MATCH (c)-[r:SIMILAR_TO]-(c2:Course)
WHERE r.similarity >= 0.6
RETURN c, r, c2;
```

## ⚙️ 설정 옵션

### 유사도 임계값 조정

임계값에 따라 그래프의 밀도가 달라집니다:

```python
# 높은 임계값 (0.7~0.9): 더 정확한 연결, 적은 엣지
edges = builder.compute_similarity(embeddings, threshold=0.7)

# 낮은 임계값 (0.3~0.5): 더 많은 연결, 많은 엣지
edges = builder.compute_similarity(embeddings, threshold=0.3)
```

**권장 임계값** (854개 교과목 기준):
- `0.3`: 광범위한 네트워크 (예상 엣지: ~50,000개)
- `0.5`: 균형잡힌 네트워크 (예상 엣지: ~10,000개)
- `0.7`: 강한 연관성만 (예상 엣지: ~2,000개)

### 임베딩 모델 변경

```python
from sentence_transformers import SentenceTransformer

# 한국어 특화 모델 (기본)
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 다른 한국어 모델
model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

# 다국어 모델
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
```

## 📁 프로젝트 구조

```
.
├── course_similarity_graph.py   # 그래프 구축 메인 모듈
├── course_graph_analysis.py     # 분석 및 추천 시스템
├── run_course_graph.py          # CLI 실행 스크립트
├── quick_start.py               # 빠른 시작 예제
├── test_similarity.py           # 유사도 테스트 (Neo4j 불필요)
├── requirements.txt             # Python 패키지 의존성
├── GUIDE.md                     # 상세 가이드
└── README.md                    # 프로젝트 개요
```

## 🎓 주요 클래스 및 메서드

### CourseGraphBuilder

그래프 구축을 담당하는 메인 클래스

**주요 메서드:**
- `load_course_data(csv_path)`: CSV 데이터 로드
- `create_embeddings(df)`: 교과목개요 기반 임베딩 생성
- `compute_similarity(embeddings, threshold)`: 유사도 계산
- `create_graph(df, edges)`: Neo4j 그래프 생성
- `get_statistics()`: 그래프 통계 조회

### CourseGraphAnalyzer

그래프 분석 및 추천을 담당하는 클래스

**주요 메서드:**
- `recommend_by_similarity(course_name, top_k)`: 유사 교과목 추천
- `recommend_by_multiple_courses(course_names, top_k)`: 복수 교과목 기반 추천
- `get_course_degree_centrality(top_k)`: 연결 중심성 분석
- `analyze_curriculum_structure(department)`: 교과과정 구조 분석
- `search_courses(keyword, category)`: 키워드 검색

## 🔧 트러블슈팅

### Neo4j 연결 오류

```python
# 연결 테스트
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", 
                              auth=("neo4j", "password"))
with driver.session() as session:
    result = session.run("RETURN 1")
    print(result.single()[0])  # 1이 출력되어야 함
```

### 메모리 부족

```python
# 배치 크기 줄이기
embeddings = model.encode(texts, batch_size=16)  # 기본값 32에서 감소
```

### 임베딩 모델 다운로드 느림

```bash
# 미리 모델 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"
```

## 📈 성능 최적화 팁

1. **임계값 조정**: 데이터 크기에 따라 적절한 임계값 선택
2. **배치 처리**: 대용량 데이터는 배치로 나누어 처리
3. **인덱스 활용**: Neo4j에서 자동으로 생성되는 인덱스 활용
4. **캐싱**: 임베딩 결과를 파일로 저장하여 재사용

## 📚 참고 자료

- [Neo4j GraphRAG Python Package](https://neo4j.com/blog/news/graphrag-python-package/)
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [Neo4j Python Driver](https://neo4j.com/docs/api/python-driver/current/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)

## 🤝 기여

버그 리포트, 기능 제안, Pull Request 환영합니다!

## 📝 라이선스

MIT License

---

**문의사항이나 도움이 필요하시면 이슈를 등록해주세요!**
