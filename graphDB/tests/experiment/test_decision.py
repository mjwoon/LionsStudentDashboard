"""비용 민감 임계값 + t* 부트스트랩 분포."""
import numpy as np
import pytest

from experiment.metrics import weighted_confusion
from experiment.pairs import SampledPair
from experiment.decision import (
    weighted_cost, cost_optimal_threshold, cost_curve, tstar_distribution,
)

THRESHOLDS = np.arange(0.30, 1.001, 0.01)


def _sample():
    # 두 층: 층0 weight=2, 층1 weight=5
    return [
        SampledPair(0, 0, 1, 0.40, 0, 2.0),  # label 0
        SampledPair(1, 0, 2, 0.72, 0, 2.0),  # label 1
        SampledPair(2, 0, 3, 0.85, 1, 5.0),  # label 1
        SampledPair(3, 0, 4, 0.90, 1, 5.0),  # label 0
    ]


LABELS = {0: 0, 1: 1, 2: 1, 3: 0}


def test_weighted_cost_is_lambda_fp_plus_fn():
    # t=0.70 에서 FP=5(pair3), FN=0 → cost = lam*5
    assert weighted_cost(_sample(), LABELS, 0.70, lam=1.0) == 5.0
    assert weighted_cost(_sample(), LABELS, 0.70, lam=3.0) == 15.0
    # t=1.01 이면 전부 미탐 → FP=0, FN=2+5=7 → lam 과 무관하게 7
    assert weighted_cost(_sample(), LABELS, 1.01, lam=9.0) == 7.0


def test_cost_optimal_threshold_monotone_in_lambda():
    """오탐 비용(lam)이 커질수록 최적 임계값은 낮아지지 않는다."""
    lams = [0.01, 0.1, 1.0, 10.0, 100.0]
    ts = [cost_optimal_threshold(_sample(), LABELS, THRESHOLDS, lam) for lam in lams]
    assert ts == sorted(ts), f"단조가 아님: {list(zip(lams, ts))}"


def test_cost_optimal_threshold_extremes():
    """극단 비용비에서는 비싼 쪽 오류가 0이 된다.

    정확한 t* 값은 단언하지 않는다 — 비용이 평탄한 구간이 존재하고
    (제거 불가능한 FP 가 남는 구간), 0.01 격자의 부동소수 표현 때문에
    경계에 정확히 놓인 쌍의 포함 여부가 갈리기 때문이다.
    의미가 있는 것은 어느 쪽 오류를 0으로 만드느냐다.
    """
    s = _sample()
    # 미탐이 비싸다(오탐은 거의 공짜) → 양성을 하나도 놓치지 않는다
    t_lo = cost_optimal_threshold(s, LABELS, THRESHOLDS, lam=1e-6)
    assert weighted_confusion(s, LABELS, t_lo)[2] == 0.0, "FN 이 0 이어야 한다"

    # 오탐이 비싸다 → 음성을 하나도 인정하지 않는다
    t_hi = cost_optimal_threshold(s, LABELS, THRESHOLDS, lam=1e9)
    assert weighted_confusion(s, LABELS, t_hi)[1] == 0.0, "FP 가 0 이어야 한다"

    assert t_hi > t_lo


def test_cost_curve_columns_and_monotonicity():
    df = cost_curve(_sample(), LABELS, THRESHOLDS, [0.25, 1.0, 4.0])
    assert set(df.columns) >= {"lam", "tstar", "precision", "recall", "f1", "fp", "fn"}
    assert len(df) == 3
    assert list(df["tstar"]) == sorted(df["tstar"])


def test_cost_curve_lambda_one_ties_to_accuracy_style_tradeoff():
    """lam=1 에서의 t* 는 가중 FP+FN 을 최소화한다 (스윕 내 최소)."""
    df = cost_curve(_sample(), LABELS, THRESHOLDS, [1.0])
    t = float(df.loc[0, "tstar"])
    best = weighted_cost(_sample(), LABELS, t, 1.0)
    assert all(weighted_cost(_sample(), LABELS, float(x), 1.0) >= best - 1e-9
               for x in THRESHOLDS)


def test_tstar_distribution_basic_stats():
    d = tstar_distribution(np.array([0.70, 0.70, 0.72, 0.68, 0.70]))
    assert d["n"] == 5
    assert d["mean"] == pytest.approx(0.70)
    assert d["median"] == pytest.approx(0.70)
    assert d["mode"] == pytest.approx(0.70)
    assert d["ci95"][0] <= d["median"] <= d["ci95"][1]
    assert d["cv"] == pytest.approx(d["sd"] / d["mean"])


def test_tstar_distribution_flags_instability():
    """넓게 퍼진 t* 는 좁은 것보다 CV 가 크다."""
    tight = tstar_distribution(np.array([0.70, 0.70, 0.71, 0.69, 0.70]))
    wide = tstar_distribution(np.array([0.45, 0.95, 0.60, 0.88, 0.70]))
    assert wide["cv"] > tight["cv"]
    assert wide["iqr"] > tight["iqr"]


def test_tstar_distribution_rejects_empty():
    with pytest.raises(ValueError):
        tstar_distribution(np.array([]))
