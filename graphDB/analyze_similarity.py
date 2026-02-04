"""유사도가 높게 나오는 원인 분석 및 TF-IDF 가중치 적용 비교"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import re

# 데이터 로드
df = pd.read_csv('final_course.csv', encoding='utf-8-sig')

print('=== 데이터 기본 정보 ===')
print(f'총 교과목 수: {len(df)}')
print(f'교과목개요 평균 길이: {df["교과목개요"].fillna("").str.len().mean():.0f}자')

# 임베딩 모델 로드
print('\n모델 로딩 중...')
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 샘플 데이터
sample_size = 100
texts_original = df['교과목개요'].fillna('').tolist()[:sample_size]

print('\n' + '='*60)
print('방법 1: 일반 임베딩 (원본 텍스트)')
print('='*60)

# 일반 임베딩
embeddings_basic = model.encode(texts_original, show_progress_bar=True)
sim_basic = cosine_similarity(embeddings_basic)
upper_basic = sim_basic[np.triu_indices(sample_size, k=1)]

print(f'\n유사도 통계:')
print(f'  평균: {upper_basic.mean():.4f}')
print(f'  표준편차: {upper_basic.std():.4f}')
print(f'  중앙값: {np.median(upper_basic):.4f}')

print(f'\n유사도 분포:')
for thresh in [0.5, 0.6, 0.7, 0.8]:
    pct = (upper_basic >= thresh).sum() / len(upper_basic) * 100
    print(f'  >= {thresh}: {pct:.1f}%')

print('\n' + '='*60)
print('방법 2: 상투적 표현 제거 후 임베딩')
print('='*60)

# 상투적 표현 리스트 (TF-IDF로 식별된 고빈도 단어들)
stopwords = {
    # 교과목개요에서 자주 등장하는 상투적 표현
    '대한', '통해', '여러', '다양한', '되는', '이해하고', '있는', '한다',
    '등을', '개념을', '위한', '능력을', '있도록', '이를', '있다', '위해',
    '이해를', '배우고', '학습한다', '익힌다', '다룬다', '강의한다',
    '수업은', '과목은', '본', '및', '등', '수', '것', '더', '또한',
    '대해', '관한', '하는', '되어', '같은', '따른', '따라', '관련',
    '기반으로', '목표로', '중심으로', '통하여', '바탕으로',
    # 일반적인 불용어
    '이', '그', '저', '것', '수', '등', '및', '또', '더', '매우',
}

def remove_stopwords(text, stopwords):
    """텍스트에서 상투적 표현 제거"""
    words = text.split()
    filtered = [w for w in words if w not in stopwords and len(w) > 1]
    return ' '.join(filtered)

# 상투적 표현 제거된 텍스트
texts_filtered = [remove_stopwords(t, stopwords) for t in texts_original]

print(f'\n상투적 표현 {len(stopwords)}개 제거')
print(f'예시 (원본): {texts_original[0][:100]}...')
print(f'예시 (제거후): {texts_filtered[0][:100]}...')

# 필터링된 텍스트로 임베딩
embeddings_filtered = model.encode(texts_filtered, show_progress_bar=True)
sim_filtered = cosine_similarity(embeddings_filtered)
upper_filtered = sim_filtered[np.triu_indices(sample_size, k=1)]

print(f'\n유사도 통계 (상투적 표현 제거):')
print(f'  평균: {upper_filtered.mean():.4f}')
print(f'  표준편차: {upper_filtered.std():.4f}')
print(f'  중앙값: {np.median(upper_filtered):.4f}')

print(f'\n유사도 분포 (상투적 표현 제거):')
for thresh in [0.5, 0.6, 0.7, 0.8]:
    pct = (upper_filtered >= thresh).sum() / len(upper_filtered) * 100
    print(f'  >= {thresh}: {pct:.1f}%')

print('\n' + '='*60)
print('방법 3: TF-IDF 유사도 (임베딩 대신 TF-IDF 벡터 직접 사용)')
print('='*60)

# TF-IDF 벡터 기반 유사도
tfidf = TfidfVectorizer(
    max_features=3000,
    min_df=2,
    max_df=0.7,  # 70% 이상 문서에 등장하면 제외
    sublinear_tf=True,
    ngram_range=(1, 2),  # 단어 + 바이그램
)
tfidf_matrix = tfidf.fit_transform(texts_original)
sim_tfidf = cosine_similarity(tfidf_matrix)
upper_tfidf = sim_tfidf[np.triu_indices(sample_size, k=1)]

print(f'\nTF-IDF 어휘 크기: {len(tfidf.get_feature_names_out())}')
print(f'\n유사도 통계 (TF-IDF 벡터):')
print(f'  평균: {upper_tfidf.mean():.4f}')
print(f'  표준편차: {upper_tfidf.std():.4f}')
print(f'  중앙값: {np.median(upper_tfidf):.4f}')

print(f'\n유사도 분포 (TF-IDF 벡터):')
for thresh in [0.3, 0.4, 0.5, 0.6]:
    pct = (upper_tfidf >= thresh).sum() / len(upper_tfidf) * 100
    print(f'  >= {thresh}: {pct:.1f}%')

print('\n' + '='*60)
print('방법 4: 임베딩 + TF-IDF 하이브리드')
print('='*60)

# 임베딩 정규화
emb_norm = embeddings_filtered / np.linalg.norm(embeddings_filtered, axis=1, keepdims=True)
tfidf_dense = tfidf_matrix.toarray()
tfidf_norm = tfidf_dense / (np.linalg.norm(tfidf_dense, axis=1, keepdims=True) + 1e-8)

# 하이브리드 유사도 (임베딩 70% + TF-IDF 30%)
sim_emb = cosine_similarity(emb_norm)
sim_tfidf_full = cosine_similarity(tfidf_norm)
sim_hybrid = 0.7 * sim_emb + 0.3 * sim_tfidf_full
upper_hybrid = sim_hybrid[np.triu_indices(sample_size, k=1)]

print(f'\n유사도 통계 (하이브리드 70% 임베딩 + 30% TF-IDF):')
print(f'  평균: {upper_hybrid.mean():.4f}')
print(f'  표준편차: {upper_hybrid.std():.4f}')
print(f'  중앙값: {np.median(upper_hybrid):.4f}')

print(f'\n유사도 분포 (하이브리드):')
for thresh in [0.5, 0.6, 0.7, 0.8]:
    pct = (upper_hybrid >= thresh).sum() / len(upper_hybrid) * 100
    print(f'  >= {thresh}: {pct:.1f}%')

print('\n' + '='*60)
print('비교 요약')
print('='*60)
print(f'{"방법":<25} {"평균":<10} {"표준편차":<10} {">= 0.7 비율":<10}')
print('-'*55)
print(f'{"1. 원본 임베딩":<25} {upper_basic.mean():<10.4f} {upper_basic.std():<10.4f} {(upper_basic >= 0.7).mean()*100:<10.1f}%')
print(f'{"2. 불용어 제거 임베딩":<25} {upper_filtered.mean():<10.4f} {upper_filtered.std():<10.4f} {(upper_filtered >= 0.7).mean()*100:<10.1f}%')
print(f'{"3. TF-IDF 벡터":<25} {upper_tfidf.mean():<10.4f} {upper_tfidf.std():<10.4f} {(upper_tfidf >= 0.7).mean()*100:<10.1f}%')
print(f'{"4. 하이브리드":<25} {upper_hybrid.mean():<10.4f} {upper_hybrid.std():<10.4f} {(upper_hybrid >= 0.7).mean()*100:<10.1f}%')

print('\n권장: 방법 2 (불용어 제거 임베딩) 또는 방법 4 (하이브리드) 사용')
print('임계값은 0.6~0.7 권장')
