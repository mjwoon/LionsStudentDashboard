"""지도학습 분류기 vs 임계값 — Kim et al. (EDM 2025) 주장의 실증 검증."""
import numpy as np
import pytest

from experiment.pairs import SampledPair
from experiment.folds import band_stratified_folds
from experiment.supervised import (
    pair_features, oof_supervised, oof_threshold_baseline, weighted_prf_from_preds,
)


def _emb(n=12, d=8, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, d))


def test_pair_features_are_symmetric():
    """대체 인정은 대칭 관계이므로 (i,j) 와 (j,i) 의 특징이 같아야 한다."""
    emb = _emb()
    a = pair_features(emb, [(2, 7)])
    b = pair_features(emb, [(7, 2)])
    assert np.allclose(a, b)


def test_pair_features_shape_is_two_blocks():
    emb = _emb(d=8)
    X = pair_features(emb, [(0, 1), (2, 3)])
    assert X.shape == (2, 16), "|u-v| 와 u*v 두 블록"


def test_folds_cover_every_pair_once_and_spread_bands():
    sample = [SampledPair(i, 0, i + 1, 0.1 * (i % 10), i % 3, 1.0) for i in range(30)]
    folds = band_stratified_folds(sample, n_folds=5, seed=0)
    assert set(folds) == {sp.pair_id for sp in sample}
    assert set(folds.values()) == set(range(5))
    # 각 층이 여러 폴드에 흩어져야 한다
    for b in {sp.bin_idx for sp in sample}:
        ids = [sp.pair_id for sp in sample if sp.bin_idx == b]
        assert len({folds[i] for i in ids}) > 1


def test_folds_reject_too_few():
    with pytest.raises(ValueError):
        band_stratified_folds([], n_folds=1)


def test_weighted_prf_matches_hand_computation():
    # 가중치 2/5, 예측·정답 지정
    preds = {0: 1, 1: 1, 2: 0, 3: 0}
    labels = {0: 1, 1: 0, 2: 1, 3: 0}
    sample = [SampledPair(0, 0, 1, .9, 0, 2.0), SampledPair(1, 0, 2, .9, 0, 2.0),
              SampledPair(2, 0, 3, .1, 1, 5.0), SampledPair(3, 0, 4, .1, 1, 5.0)]
    p, r, f = weighted_prf_from_preds(sample, labels, preds)
    # TP=2, FP=2, FN=5 -> P=0.5, R=2/7
    assert p == pytest.approx(0.5)
    assert r == pytest.approx(2 / 7)


def test_supervised_learns_a_separable_signal():
    """특징이 레이블을 완전히 가르면 out-of-fold 로도 높은 F1 이 나와야 한다."""
    rng = np.random.default_rng(1)
    n = 80
    emb = np.zeros((n + 1, 4))
    labels, sample = {}, []
    for i in range(n):
        y = i % 2
        # 양성은 두 벡터가 가깝고 음성은 멀도록
        emb[i] = rng.normal(scale=0.01, size=4) + (0 if y else 5)
        labels[i] = y
        sample.append(SampledPair(i, i, n, 0.5, i % 3, 1.0))
    X = pair_features(emb, [(sp.i, sp.j) for sp in sample])
    preds, _ = oof_supervised(sample, labels, X, n_folds=4, seed=0)
    _, _, f1 = weighted_prf_from_preds(sample, labels, preds)
    assert f1 > 0.8, f"분리 가능한 신호를 학습하지 못했다 (F1={f1})"


def test_supervised_does_not_hallucinate_signal_from_noise():
    rng = np.random.default_rng(2)
    n = 80
    emb = rng.normal(size=(n + 1, 6))
    labels = {i: int(rng.integers(0, 2)) for i in range(n)}
    sample = [SampledPair(i, i, n, 0.5, i % 3, 1.0) for i in range(n)]
    X = pair_features(emb, [(sp.i, sp.j) for sp in sample])
    preds, _ = oof_supervised(sample, labels, X, n_folds=4, seed=0)
    _, _, f1 = weighted_prf_from_preds(sample, labels, preds)
    assert f1 < 0.75, f"무작위 레이블에서 F1={f1} — 누수 의심"


def test_threshold_baseline_is_fit_on_train_fold_only():
    """임계값도 학습 폴드에서 고르고 시험 폴드에 적용해야 공정하다."""
    sample = [SampledPair(i, 0, i + 1, i / 40, i % 3, 1.0) for i in range(40)]
    labels = {i: int(i / 40 >= 0.5) for i in range(40)}
    preds, ts = oof_threshold_baseline(sample, labels,
                                       np.arange(0.30, 1.001, 0.01), n_folds=4, seed=0)
    assert set(preds) == {sp.pair_id for sp in sample}
    assert len(ts) == 4, "폴드마다 임계값이 하나씩 선택돼야 한다"
    _, _, f1 = weighted_prf_from_preds(sample, labels, preds)
    assert f1 > 0.8


def test_sweep_covers_grid_and_is_sorted():
    from experiment.supervised import sweep_supervised, feature_sets, model_zoo
    rng = np.random.default_rng(3)
    n = 40
    emb = rng.normal(size=(n + 1, 5))
    labels = {i: int(i % 2) for i in range(n)}
    sample = [SampledPair(i, i, n, 0.5 + 0.01 * i, i % 3, 1.0) for i in range(n)]
    df = sweep_supervised(sample, labels, emb, n_folds=3, seed=0)
    expected = len(feature_sets(emb, [(0, 1)], [0.5])) * len(model_zoo())
    assert len(df) == expected
    assert list(df["f1"]) == sorted(df["f1"], reverse=True), "F1 내림차순이어야 한다"
    assert df["f1"].between(0, 1).all()


def test_feature_sets_include_kim_difference_vector():
    """Kim 등이 쓴 형태(차이 벡터 단독)가 후보에 있어야 공정한 비교다."""
    from experiment.supervised import feature_sets
    emb = _emb(d=6)
    fs = feature_sets(emb, [(0, 1), (2, 3)], [0.5, 0.6])
    assert "diff" in fs
    assert fs["diff"].shape[1] == 6
