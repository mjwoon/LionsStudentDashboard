"""두 과목 유사도 디버깅"""
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv('final_course.csv', encoding='utf-8-sig')

# 두 과목 찾기
prog_rows = df[df['교과목 이름'] == '프로그래밍기초']
space_rows = df[df['교과목 이름'] == '현대우주탐사및추진시스템기초']

print('=== 프로그래밍기초 (총 {}개) ==='.format(len(prog_rows)))
for i, row in prog_rows.iterrows():
    print(f"학과: {row['설강학과']}")
    print(f"개요: {row['교과목개요'][:150]}...")
    print()

print('=== 현대우주탐사및추진시스템기초 ===')
for i, row in space_rows.iterrows():
    print(f"학과: {row['설강학과']}")
    print(f"개요: {row['교과목개요'][:150]}...")
    print()

# 임베딩 모델 - 다국어 모델로 테스트
print('\n=== 다국어 모델 (paraphrase-multilingual-MiniLM-L12-v2) ===')
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

# 모든 프로그래밍기초와 현대우주탐사 간 유사도 계산
print('=== 유사도 계산 ===')
for _, prog in prog_rows.iterrows():
    for _, space in space_rows.iterrows():
        texts = [prog['교과목개요'], space['교과목개요']]
        embs = model.encode(texts)
        sim = cosine_similarity([embs[0]], [embs[1]])[0][0]
        print(f"프로그래밍기초({prog['설강학과']}) <-> 현대우주탐사: {sim:.4f}")

# 비교용: 프로그래밍기초와 실제로 유사해야 하는 과목
print('\n=== 비교: 프로그래밍기초 vs 다른 프로그래밍 과목 ===')
prog_text = prog_rows.iloc[0]['교과목개요']

compare_courses = ['C++/JAVA프로그래밍', 'AI+X:R-Py컴퓨팅', '공업수학1']
for course_name in compare_courses:
    course = df[df['교과목 이름'] == course_name]
    if len(course) > 0:
        texts = [prog_text, course.iloc[0]['교과목개요']]
        embs = model.encode(texts)
        sim = cosine_similarity([embs[0]], [embs[1]])[0][0]
        print(f"프로그래밍기초 <-> {course_name}: {sim:.4f}")
