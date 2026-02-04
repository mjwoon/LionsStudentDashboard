# GraphDB 프로젝트 분석 및 변경 이력

## 📋 프로젝트 개요

교과목 유사도 기반 그래프 네트워크를 구축하여 학생들에게 유사 과목 추천 및 교과과정 분석 기능을 제공합니다.

### 기술 스택
- **그래프 데이터베이스**: Neo4j
- **임베딩 모델**: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- **유사도 계산**: 코사인 유사도 + TF-IDF 하이브리드
- **언어**: Python 3.x

### 핵심 파일
| 파일 | 설명 |
|------|------|
| `course_similarity_graph.py` | 그래프 빌더 클래스 (핵심 로직) |
| `quick_start.py` | 실행 엔트리포인트 |
| `course_graph_analysis.py` | 그래프 분석 유틸리티 |
| `final_course.csv` | 교과목 데이터 (354개 과목) |

---

## 🔄 변경 이력

### 1. 임베딩 모델 변경 (한국어 → 다국어)

**문제점**
- 기존 한국어 전용 모델 (`jhgan/ko-sroberta-multitask`) 사용
- 영어 강의 과목들("프로그래밍기초(영어)", "현대우주탐사(영어)" 등)이 비정상적으로 높은 유사도(0.73) 기록
- 한국어 모델이 영어 텍스트를 "알 수 없는 외국어"로 인식하여 모두 유사하게 처리

**해결책**
```python
# 변경 전
self.embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 변경 후
self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
```

**결과**
- "프로그래밍기초(영어)" ↔ "현대우주탐사(영어)" 유사도: 0.73 → **0.42**
- 50개 이상 언어 지원으로 한국어/영어 혼합 데이터 정확히 처리

---

### 2. TF-IDF 하이브리드 유사도 적용

**문제점**
- 교과목 설명에 상투적 표현이 많아 의미 없이 높은 유사도 발생
- 예: "본 과목은 ~에 대해 학습한다", "~능력을 배양한다" 등

**해결책**
1. **상투적 표현 제거** (49개 단어)
```python
stopwords = {
    '대한', '통해', '여러', '다양한', '되는', '이해하고', '있는', '한다',
    '등을', '개념을', '위한', '능력을', '있도록', '이를', '있다', '위해',
    '이해를', '배우고', '학습한다', '익힌다', '다룬다', '강의한다',
    '수업은', '과목은', '본', '및', '등', '수', '것', '더', '또한',
    '대해', '관한', '하는', '되어', '같은', '따른', '따라', '관련',
    '기반으로', '목표로', '중심으로', '통하여', '바탕으로',
    '이', '그', '저', '것', '수', '등', '및', '또', '더', '매우',
}
```

2. **하이브리드 유사도 계산**

#### 임베딩 유사도란?
임베딩(Embedding)은 텍스트를 고차원 벡터 공간에 매핑하는 기술입니다. 의미적으로 유사한 텍스트는 벡터 공간에서 가까운 위치에 배치됩니다.

```
"미분적분학" → [0.23, -0.45, 0.12, ..., 0.67]  (384차원 벡터)
"선형대수학" → [0.21, -0.42, 0.15, ..., 0.63]  (유사한 벡터)
"영어회화"   → [-0.56, 0.33, -0.21, ..., 0.11] (다른 벡터)
```

**코사인 유사도**로 두 벡터 간 각도를 측정합니다:
- 1.0: 완전히 동일한 방향 (매우 유사)
- 0.0: 직교 (관련 없음)
- -1.0: 반대 방향

```python
cosine_similarity(embedding_A, embedding_B)
```

#### 하이브리드 방식을 사용하는 이유
| 방식 | 장점 | 단점 |
|------|------|------|
| 임베딩만 | 의미적 유사도 포착 | 상투적 표현에 민감 |
| TF-IDF만 | 키워드 기반 정확도 | 동의어/유사 표현 놓침 |
| **하이브리드** | 두 장점 결합 | - |

#### 최종 공식
```
최종 유사도 = 70% × 임베딩 유사도 + 30% × TF-IDF 유사도
```

3. **TF-IDF 설정**
```python
TfidfVectorizer(
    max_features=3000,
    min_df=2,
    max_df=0.7,  # 70% 이상 문서에 등장하면 제외
    sublinear_tf=True,
    ngram_range=(1, 2),
)
```

---

### 3. 연계 과목 필터링 추가

**문제점**
- "미분적분학1" ↔ "미분적분학2" 같은 연계(선수-후수) 과목이 유사 과목으로 분류됨
- 실제로는 순차적으로 수강해야 하는 과목들

**해결책**
`_is_sequential_course()` 메서드 추가:

```python
def _is_sequential_course(self, name1: str, name2: str) -> bool:
    """
    두 과목이 연계 과목(1, 2 시리즈)인지 확인
    예: 미분적분학1 vs 미분적분학2
    """
    # 끝에 붙은 숫자/로마자 패턴 감지
    # 1, 2, I, II, Ⅰ, Ⅱ 등
```

**감지 패턴**
| 패턴 | 예시 |
|------|------|
| 아라비아 숫자 | 미분적분학1 ↔ 미분적분학2 |
| 로마 숫자 (ASCII) | 물리학및실험I ↔ 물리학및실험II |
| 로마 숫자 (유니코드) | 과목명Ⅰ ↔ 과목명Ⅱ |

**결과**
- **130개** 연계 과목 쌍이 SIMILAR_TO 관계에서 제외됨

---

### 4. 동일 학수번호 관계 추가 (IDENTICAL_ID)

**배경**
- 같은 학수번호(예: GEN0063)가 여러 학과에서 개설되는 경우
- 예: "일반물리학1"이 13개 학과에서 동일 학수번호로 개설

**구현**
```python
def compute_identical_id_edges(self, df: pd.DataFrame) -> List[Tuple[int, int, str, str]]:
    """학수번호는 동일하나 설강학과가 다른 교과목 쌍 찾기"""
```

**Neo4j 관계 타입**
- `SIMILAR_TO`: 내용 기반 유사도 (임베딩)
- `IDENTICAL_ID`: 학수번호 기반 동일 과목 (다른 학과)

---

### 5. E5 모델 테스트 및 롤백

**시도**
- Microsoft의 `intfloat/multilingual-e5-small` 모델 테스트
- 검색/유사도 작업에 특화된 모델

**결과**
| 임계값 | MiniLM | E5-small |
|--------|--------|----------|
| 0.5 | 493개 | 62,023개 |
| 0.6 | - | 11,787개 |
| 0.65 | - | 346개 |
| 0.7 | - | 38개 |

**결론**
- E5 모델은 유사도 분포가 전반적으로 높음
- 임계값 조정이 필요하고 결과 일관성이 떨어짐
- **MiniLM 모델로 롤백** (안정적인 결과)

---

## 📊 최종 그래프 통계

| 항목 | 값 |
|------|-----|
| 총 교과목 수 | 354개 |
| 유사도 엣지 (SIMILAR_TO) | 493개 |
| 학수번호 엣지 (IDENTICAL_ID) | 227개 |
| 평균 유사도 | 0.5529 |
| 유사도 임계값 | 0.5 |
| 스킵된 동일 학수번호 쌍 | 227개 |
| 스킵된 연계 과목 쌍 | 130개 |

### 허브 교과목 (가장 많은 연결)
1. 공업수학1 - 24개 연결
2. 경제수학 - 20개 연결
3. 기초미분적분학 - 17개 연결
4. CORE기초물리학 - 17개 연결
5. 인공지능기초프로그래밍 - 13개 연결

---

## 🔍 Neo4j Cypher 쿼리 예제

### 유사 교과목 조회
```cypher
MATCH (c:Course {name: '데이터베이스'})-[r:SIMILAR_TO]-(c2:Course)
RETURN c2.name, c2.department, r.similarity
ORDER BY r.similarity DESC
LIMIT 10
```

### 동일 학수번호 과목 조회
```cypher
MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
RETURN c.name, c.department, c2.department, c.code
LIMIT 20
```

### 특정 학과 네트워크
```cypher
MATCH (c:Course)
WHERE c.department CONTAINS '컴퓨터'
OPTIONAL MATCH (c)-[r:SIMILAR_TO]-(c2:Course)
WHERE c2.department CONTAINS '컴퓨터'
RETURN c, r, c2
```

### 학수번호별 공유 학과 통계
```cypher
MATCH (c:Course)-[r:IDENTICAL_ID]-(c2:Course)
WITH c.code as course_code, 
     collect(DISTINCT c.department) + collect(DISTINCT c2.department) as depts
RETURN course_code, size(depts) as dept_count
ORDER BY dept_count DESC
LIMIT 10
```

---

## 🚀 실행 방법

```bash
# Neo4j 실행 (Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:latest

# 그래프 빌드
cd graphDB
uv run python quick_start.py

# Neo4j Browser 접속
# http://localhost:7474
```

---

## 📝 향후 개선 사항

1. **선수과목 관계 추가**: 실제 선수과목 데이터 기반 `PREREQUISITE` 관계
2. **학년별 추천**: 학년/학기 정보 활용한 순차적 추천
3. **클러스터링**: 유사 과목 그룹화 (커뮤니티 탐지)
4. **실시간 업데이트**: 새 과목 추가 시 증분 업데이트

---

*마지막 업데이트: 2026년 2월 5일*
