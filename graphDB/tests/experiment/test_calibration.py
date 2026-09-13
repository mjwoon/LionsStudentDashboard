"""유사도 → 대체 인정 확률 보정(isotonic)과 비용 최적 결정 규칙."""
import numpy as np
import pytest

from experiment.pairs import SampledPair
from experiment.calibration import (
    fit_isotonic, calibrated_threshold, cost_optimal_probability,
    weighted_brier, cross_val_probabilities,
)


def _sample():
    # 유사도가 높을수록 양성이 잦은 구조 (층0 weight=2, 층1 weight=5)
    sims = [0.10, 0.20, 0.30, 0.45, 0.55, 0.62, 0.71, 0.78, 0.85, 0.93]
    ys = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
    return ([SampledPair(i, 0, i + 1, s, 0 if s < 0.6 else 1, 2.0 if s < 0.6 else 5.0)
             for i, s in enumerate(sims)],
            {i: y for i, y in enumerate(ys)})


def test_cost_optimal_probability_is_bayes_rule():
    """비용 최적 결정 경계는 P >= lam/(1+lam) 이다."""
    assert cost_optimal_probability(1.0) == pytest.approx(0.5)
    assert cost_optimal_probability(3.0) == pytest.approx(0.75)
    assert cost_optimal_probability(1 / 3) == pytest.approx(0.25)
    # 오탐이 공짜면 무조건 인정, 무한히 비싸면 절대 인정 안 함
    assert cost_optimal_probability(0.0) == pytest.approx(0.0)
    assert cost_optimal_probability(1e12) > 0.999


def test_cost_optimal_probability_rejects_negative():
    with pytest.raises(ValueError):
        cost_optimal_probability(-1.0)


def test_isotonic_is_monotone_nondecreasing():
    sample, labels = _sample()
    iso = fit_isotonic(sample, labels)
    grid = np.linspace(0, 1, 101)
    p = iso.predict(grid)
    assert np.all(np.diff(p) >= -1e-12), "보정된 확률은 유사도에 대해 단조여야 한다"
    assert p.min() >= 0.0 and p.max() <= 1.0


def test_calibrated_threshold_inverts_the_curve():
    sample, labels = _sample()
    iso = fit_isotonic(sample, labels)
    for p_target in (0.25, 0.5, 0.75):
        t = calibrated_threshold(iso, p_target)
        assert float(iso.predict([t])[0]) >= p_target - 1e-9
        # 그 바로 아래는 목표 미달이어야 한다(최소 임계값)
        if t > 0.001:
            assert float(iso.predict([t - 0.01])[0]) < p_target


def test_calibrated_threshold_monotone_in_target():
    sample, labels = _sample()
    iso = fit_isotonic(sample, labels)
    ts = [calibrated_threshold(iso, p) for p in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert ts == sorted(ts), f"목표 확률이 높을수록 임계값도 높아야 한다: {ts}"


def test_calibrated_threshold_unreachable_target_returns_above_max():
    """도달 불가능한 목표는 스윕 상한 위를 돌려준다(= 아무것도 인정하지 않음)."""
    sample, labels = _sample()
    iso = fit_isotonic(sample, labels)
    assert calibrated_threshold(iso, 1.5) > 1.0


def test_weighted_brier_rewards_accuracy_and_respects_weights():
    y = [1, 0]
    assert weighted_brier([1.0, 0.0], y, [1.0, 1.0]) == pytest.approx(0.0)
    assert weighted_brier([0.0, 1.0], y, [1.0, 1.0]) == pytest.approx(1.0)
    # 틀린 쪽 가중치가 크면 점수가 나빠진다
    light = weighted_brier([0.5, 0.0], y, [1.0, 100.0])
    heavy = weighted_brier([0.5, 0.0], y, [100.0, 1.0])
    assert heavy > light


def test_cross_val_probabilities_are_out_of_fold_and_complete():
    sample, labels = _sample()
    p = cross_val_probabilities(sample, labels, n_folds=3, seed=0)
    assert set(p) == {sp.pair_id for sp in sample}
    assert all(0.0 <= v <= 1.0 for v in p.values())


def test_cross_val_beats_nothing_on_pure_noise():
    """레이블이 유사도와 무관하면 보정 곡선이 정보를 만들어내지 못한다."""
    rng = np.random.default_rng(0)
    sims = rng.uniform(0, 1, 60)
    sample = [SampledPair(i, 0, i + 1, float(s), 0, 1.0) for i, s in enumerate(sims)]
    labels = {i: int(rng.integers(0, 2)) for i in range(60)}
    p = cross_val_probabilities(sample, labels, n_folds=4, seed=0)
    ys = [labels[sp.pair_id] for sp in sample]
    ps = [p[sp.pair_id] for sp in sample]
    base = np.mean(ys)
    # 무작위 레이블에서 out-of-fold Brier 가 상수 예측보다 크게 좋아질 수 없다
    assert weighted_brier(ps, ys, [1.0] * 60) > weighted_brier(
        [base] * 60, ys, [1.0] * 60) - 0.05
