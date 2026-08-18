import numpy as np
import pandas as pd
from experiment.pairs import valid_pair_indices, compute_hybrid_similarity, SampledPair


def _df():
    # 학수번호 중복(SAME) 1쌍과 연계과목(미적분학1/미적분학2) 1쌍이 제외되어야 한다.
    # 개요는 프로덕션 TF-IDF(min_df=2)에서 살아남도록 2개 문서에 공유되는 어휘를 넣는다.
    return pd.DataFrame({
        "교과목 이름": ["미적분학1", "미적분학2", "물리학", "화학"],
        "교과목개요": ["미분 극한 함수", "적분 함수 미분", "역학 힘 운동", "화학 반응 운동"],
        "학수번호": ["X1", "X2", "SAME", "SAME"],
    })


def test_valid_pairs_excludes_same_code_and_sequential():
    pairs = valid_pair_indices(_df())
    got = {tuple(p) for p in pairs}
    # (0,1)=연계 제외, (2,3)=같은 학수번호 제외. 나머지 4쌍만 유효.
    assert (0, 1) not in got and (2, 3) not in got
    assert len(got) == 4


def test_hybrid_similarity_is_symmetric_with_injected_model():
    df = _df()

    # 주입 모델: 고정 임베딩 → SBERT 다운로드 없이 테스트
    class FakeModel:
        def encode(self, texts, **kw):
            rng = np.random.default_rng(0)
            return rng.random((len(texts), 8))

    from similarity_engine import SimilarityEngine
    eng = SimilarityEngine(model=FakeModel())
    sim = compute_hybrid_similarity(df, engine=eng)
    assert sim.shape == (4, 4)
    assert np.allclose(sim, sim.T, atol=1e-6)
