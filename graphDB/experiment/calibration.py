r"""유사도 점수를 대체 인정 확률로 보정(isotonic)하고, 비용에서 임계값을 유도한다.

임베딩 코사인 유사도는 **보정되지 않은 값**이다. 등위는 신뢰할 수 있지만
"0.70"이라는 절대값 자체는 해석 가능한 척도가 아니며, 그래서 임계값을 도메인마다
경험적으로 정해야 한다. 여기서는 한 걸음 더 나아가 유사도를 확률로 옮긴다.

    P(대체 인정 가능 | 유사도 = s)

등위 보존 회귀(isotonic)는 단조성만 가정하므로, 유사도의 등위는 신뢰하되 눈금은
신뢰하지 않는다는 이 문제의 전제와 정확히 맞는다.

확률로 옮기면 임계값이 비용에서 **유도된다.** 오탐 비용 c_FP, 미탐 비용 c_FN 에
대해 인정의 기대비용이 거절보다 작을 조건은

    (1 - P)·c_FP < P·c_FN   <=>   P > c_FP / (c_FP + c_FN) = lam / (1 + lam)

즉 비용비 lam 하나가 확률 공간의 결정 경계를 정하고, 보정 곡선을 거꾸로 타면
유사도 임계값이 나온다. 스윕에서 비용을 직접 최소화한 `decision.cost_curve` 와
서로 독립인 두 경로이므로, 둘이 일치하면 상호 검증이 된다.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression

from experiment.folds import band_stratified_folds

# 보정 곡선을 역으로 탈 때 쓰는 유사도 격자
GRID_LO, GRID_HI, GRID_STEP = 0.0, 1.0, 0.001


def fit_isotonic(sample, labels, use_weights: bool = True) -> IsotonicRegression:
    """유사도 -> P(양성) 등위 보존 회귀.

    표본이 유사도 구간으로 층화돼 있으므로 조건부 P(y|sim) 자체는 층화에
    편향되지 않는다(층 내 가중치가 상수라 서로 상쇄된다). 그럼에도 기본으로
    HT 가중을 넣는 것은 폭이 넓은 하위 층에서 층 간 풀링 비중을 모집단에
    맞추기 위해서다. `use_weights=False` 로 끄고 비교할 수 있다.
    """
    x = np.array([sp.sim for sp in sample], dtype=float)
    y = np.array([labels[sp.pair_id] for sp in sample], dtype=float)
    w = np.array([sp.weight for sp in sample], dtype=float) if use_weights else None
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip")
    iso.fit(x, y, sample_weight=w)
    return iso


def calibrated_threshold(iso: IsotonicRegression, p_target: float) -> float:
    """P(양성) >= p_target 이 되는 최소 유사도. 도달 불가능하면 격자 상한 위."""
    grid = np.arange(GRID_LO, GRID_HI + GRID_STEP / 2, GRID_STEP)
    p = iso.predict(grid)
    hit = np.nonzero(p >= p_target - 1e-12)[0]
    if hit.size == 0:
        return float(GRID_HI + GRID_STEP)
    return float(grid[hit[0]])


def cost_optimal_probability(lam: float) -> float:
    """비용비 lam = c_FP/c_FN 에서의 결정 경계 확률 lam/(1+lam)."""
    if lam < 0:
        raise ValueError(f"비용비는 음수일 수 없습니다: {lam}")
    return float(lam / (1.0 + lam))


def weighted_brier(probs, labels, weights) -> float:
    """가중 Brier 점수(낮을수록 좋음)."""
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    w = np.asarray(weights, dtype=float)
    return float(np.sum(w * (p - y) ** 2) / np.sum(w))


def cross_val_probabilities(sample, labels, n_folds: int = 5, seed: int = 42) -> dict:
    """층 내 분할 교차검증으로 얻은 out-of-fold 보정 확률.

    335쌍에 isotonic 을 그대로 적합하면 과적합한다. 폴드를 층(bin_idx) 안에서
    나눠 각 층의 유사도 분포가 모든 폴드에 고르게 들어가게 한다.
    """
    folds = band_stratified_folds(sample, n_folds=n_folds, seed=seed)
    out = {}
    for k in range(n_folds):
        train = [sp for sp in sample if folds[sp.pair_id] != k]
        test = [sp for sp in sample if folds[sp.pair_id] == k]
        if not test:
            continue
        if len({labels[sp.pair_id] for sp in train}) < 2:
            # 학습 폴드에 한 클래스만 있으면 그 상수를 예측한다
            const = float(next(iter({labels[sp.pair_id] for sp in train})))
            for sp in test:
                out[sp.pair_id] = const
            continue
        iso = fit_isotonic(train, labels)
        for sp, p in zip(test, iso.predict([sp.sim for sp in test])):
            out[sp.pair_id] = float(np.clip(p, 0.0, 1.0))
    return out
