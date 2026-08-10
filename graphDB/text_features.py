"""
graphDB 파이프라인 공유 텍스트/피처 프리미티브 (단일 출처).

이 모듈은 그동안 course_similarity_graph.py, threshold_experiment.py,
analyze_similarity.py 에 복붙으로 흩어져 있던 도메인 상수·순수 함수를 한 곳으로
모은 것이다.

  - 상투적 표현(STOPWORDS) 세트
  - 선수강 매칭 전용 확장 세트(PREREQ_STOPWORDS)
  - stopword 필터링
  - 연계과목(1/2 시리즈) 판별
  - TF-IDF 벡터라이저 설정

주의: 이 모듈은 graphDB 빌드타임 전용이며 lions-core(백엔드 공유 패키지)와 무관하다.
ADR 0001의 결정에 따라 graphDB는 workspace 멤버가 아니라 독립 스크립트 루트로 유지되므로,
SBERT/TF-IDF/유사도 로직은 여기(graphDB)에 남는다.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from sklearn.feature_extraction.text import TfidfVectorizer


# 프로덕션 임베딩 모델 (영어+한국어 혼합 데이터에 적합한 다국어 모델).
# analyze_similarity.py 는 "모델 비교"가 목적이므로 의도적으로 다른 모델을 쓴다.
PRODUCTION_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# ── 상투적 표현(불용어) ────────────────────────────────────────────────
# 교과목개요/이름 임베딩·TF-IDF 시 제거하는 관용 표현. frozenset 이라 멤버십 검사에
# 그대로 쓸 수 있고, 실수로 변형되는 것을 막는다.
STOPWORDS: frozenset[str] = frozenset({
    '대한', '통해', '여러', '다양한', '되는', '이해하고', '있는', '한다',
    '등을', '개념을', '위한', '능력을', '있도록', '이를', '있다', '위해',
    '이해를', '배우고', '학습한다', '익힌다', '다룬다', '강의한다',
    '수업은', '과목은', '본', '및', '등', '수', '것', '더', '또한',
    '대해', '관한', '하는', '되어', '같은', '따른', '따라', '관련',
    '기반으로', '목표로', '중심으로', '통하여', '바탕으로',
    '이', '그', '저', '또', '매우',
})

# 선수강 과목명 매칭 전용: 일반 불용어 + 선수강 요건 문구의 관용어.
# 예) "미분적분학1 수강 필요" → 과목명 "미분적분학1"만 남기기 위함.
PREREQ_STOPWORDS: frozenset[str] = STOPWORDS | frozenset({
    '수강하셨으면', '필수', '요구', '요구됨', '필요', '필요함', '필요합니다',
    '수강', '선수강', '추천', '좋습니다', '아닙니다',
})


def filter_stopwords(text: str, stopwords: Iterable[str] = STOPWORDS) -> str:
    """텍스트에서 불용어와 1글자 토큰을 제거해 공백으로 join."""
    sw = stopwords if isinstance(stopwords, (set, frozenset)) else set(stopwords)
    return ' '.join(w for w in text.split() if w not in sw and len(w) > 1)


def filter_stopwords_many(
    texts: Iterable[str], stopwords: Iterable[str] = STOPWORDS
) -> list[str]:
    """여러 텍스트에 filter_stopwords 를 일괄 적용."""
    sw = stopwords if isinstance(stopwords, (set, frozenset)) else set(stopwords)
    return [filter_stopwords(t, sw) for t in texts]


# ── 연계과목(1/2 시리즈) 판별 ──────────────────────────────────────────
_SEQ_TRAILING = re.compile(r'[0-9IⅠⅡ]+$')
_PAREN_TRAILING = re.compile(r'\([^)]*\)$')


def _base_name(name: str) -> str:
    """끝에 붙은 숫자/로마자와 괄호 내용을 제거한 기본 과목명."""
    base = _SEQ_TRAILING.sub('', name.strip())
    base = _PAREN_TRAILING.sub('', base.strip())
    return base.strip()


def _sequence_num(name: str) -> Optional[str]:
    """끝에 붙은 시퀀스 번호(로마자→아라비아 정규화). 없으면 None."""
    m = _SEQ_TRAILING.search(name.strip())
    if not m:
        return None
    return (m.group(0)
            .replace('Ⅰ', '1').replace('Ⅱ', '2')
            .replace('I', '1').replace('II', '2'))


def is_sequential_course(name1: str, name2: str) -> bool:
    """
    두 과목이 연계 과목(1, 2 시리즈)인지 판별.
    예: 미분적분학1 vs 미분적분학2, 일반물리학1 vs 일반물리학2

    기본 이름이 같고, 둘 다 시퀀스 번호가 있으며, 번호가 다르면 True.
    """
    b1, b2 = _base_name(name1), _base_name(name2)
    s1, s2 = _sequence_num(name1), _sequence_num(name2)
    return bool(b1 == b2 and s1 and s2 and s1 != s2)


# ── TF-IDF 벡터라이저 설정 (단일 출처) ─────────────────────────────────
def build_outline_tfidf() -> TfidfVectorizer:
    """
    교과목개요 기반 단어/바이그램 TF-IDF.
    max_df=0.7 로 70% 이상 문서에 등장하는 상투적 표현을 제외한다.
    """
    return TfidfVectorizer(
        max_features=3000,
        min_df=2,
        max_df=0.7,
        sublinear_tf=True,
        ngram_range=(1, 2),
    )


def build_name_char_tfidf() -> TfidfVectorizer:
    """
    교과목 '이름' char n-gram TF-IDF (threshold 실험의 GT 생성 전용).
    개요와 독립적인 신호를 얻기 위해 char_wb (2,4)-gram 을 쓴다.
    """
    return TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(2, 4),
        min_df=1,
    )
