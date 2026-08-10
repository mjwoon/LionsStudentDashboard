"""SimilarityEngine 순수 계산 단위 테스트.

임베딩은 직접 주입하고, 임베딩 모델은 결정적 FakeModel 로 대체하여
SentenceTransformer 다운로드 없이 계산 로직만 검증한다.
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from similarity_engine import SimilarityEngine  # noqa: E402


class FakeModel:
    """encode(texts) -> 사전에 지정한 벡터를 그대로 반환."""

    def __init__(self, mapping):
        self.mapping = mapping

    def encode(self, texts, **kwargs):
        return np.array([self.mapping[t] for t in texts], dtype=float)


class ComputeSimilarityTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimilarityEngine(model=object())  # 모델은 사용되지 않음

    def test_skips_same_code_and_sequential(self):
        df = pd.DataFrame({
            "교과목 이름": ["미분적분학1", "미분적분학2", "선형대수"],
            "학수번호": ["MATH101", "MATH201", "MATH101"],
        })
        # 모든 쌍 유사도 1.0 (동일 벡터)
        embeddings = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
        edges = self.engine.compute_similarity(df, embeddings, threshold=0.5)

        # (0,1) 연계과목 skip, (0,2) 동일 학수번호 skip → (1,2)만 남음
        self.assertEqual([(i, j) for i, j, _ in edges], [(1, 2)])
        self.assertAlmostEqual(edges[0][2], 1.0, places=6)

    def test_threshold_filters(self):
        df = pd.DataFrame({
            "교과목 이름": ["A", "B"],
            "학수번호": ["X1", "X2"],
        })
        embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])  # 유사도 0
        self.assertEqual(self.engine.compute_similarity(df, embeddings, threshold=0.5), [])


class ComputeIdenticalIdTest(unittest.TestCase):
    def test_same_code_different_dept(self):
        engine = SimilarityEngine(model=object())
        df = pd.DataFrame({
            "학수번호": ["C1", "C1", "C1", "C2"],
            "설강학과": ["컴퓨터", "전자", "컴퓨터", "수학"],
            "교과목 이름": ["a", "b", "c", "d"],
        })
        edges = engine.compute_identical_id_edges(df)
        # C1 그룹에서 학과가 다른 쌍만: (0,1)컴퓨터-전자, (1,2)전자-컴퓨터. (0,2)동일학과 제외
        pairs = {(i, j) for i, j, _, _ in edges}
        self.assertEqual(pairs, {(0, 1), (1, 2)})

    def test_blank_codes_are_not_grouped(self):
        # 미매칭으로 빈 학수번호가 다수여도 가짜 IDENTICAL_ID 엣지가 생기면 안 된다.
        engine = SimilarityEngine(model=object())
        df = pd.DataFrame({
            "학수번호": ["", "", "C1"],
            "설강학과": ["컴퓨터", "전자", "수학"],
            "교과목 이름": ["a", "b", "c"],
        })
        self.assertEqual(engine.compute_identical_id_edges(df), [])


class ComputePrerequisiteTest(unittest.TestCase):
    def test_exact_match(self):
        engine = SimilarityEngine(model=object())  # 정확일치만 → 모델 미사용
        df = pd.DataFrame({
            "교과목 이름": ["자료구조", "알고리즘"],
            "선수강 과목": ["", "자료구조"],
        })
        embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
        edges, unmapped = engine.compute_prerequisite_edges(df, embeddings, threshold=0.6)
        self.assertEqual(edges, [(1, 0, 1.0, "자료구조")])
        self.assertEqual(unmapped, {})

    def test_semantic_match_batched(self):
        # '자료구조기초'는 정확일치 실패 → 배치 인코딩 후 course1(=자료구조 벡터)과 매칭
        engine = SimilarityEngine(model=FakeModel({"자료구조기초": [0.0, 1.0]}))
        df = pd.DataFrame({
            "교과목 이름": ["알고리즘", "자료구조"],
            "선수강 과목": ["자료구조기초", ""],
        })
        course_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
        edges, unmapped = engine.compute_prerequisite_edges(
            df, course_embeddings, threshold=0.6
        )
        self.assertEqual(len(edges), 1)
        src, tgt, score, raw = edges[0]
        self.assertEqual((src, tgt, raw), (0, 1, "자료구조기초"))
        self.assertGreaterEqual(score, 0.6)
        self.assertEqual(unmapped, {})

    def test_unmapped_when_below_threshold(self):
        # 어떤 과목과도 최대 코사인 0.8 → threshold 0.99 미달로 미매핑 처리
        engine = SimilarityEngine(model=FakeModel({"애매한과목": [0.6, 0.8]}))
        df = pd.DataFrame({
            "교과목 이름": ["알고리즘", "자료구조"],
            "선수강 과목": ["애매한과목", ""],
        })
        course_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
        edges, unmapped = engine.compute_prerequisite_edges(
            df, course_embeddings, threshold=0.99
        )
        self.assertEqual(edges, [])
        self.assertEqual(unmapped, {0: ["애매한과목"]})


if __name__ == "__main__":
    unittest.main()
