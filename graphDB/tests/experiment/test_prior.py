"""하위 구간 양성 수의 비식별성과 재현율 민감도."""
import numpy as np
import pytest

from experiment.prior import (
    prob_zero_in_stratum, observation_probability, max_consistent_M,
    recall_under_hypothesis, sensitivity_table, name_collision_candidates,
)

# RQ1 실측: 양성 0건이 관측된 두 층
STRATA = [(1_100_048, 100), (6_984, 60)]


def test_prob_zero_is_one_when_no_positives():
    assert prob_zero_in_stratum(1000, 50, 0) == 1.0


def test_prob_zero_is_zero_when_almost_all_positive():
    assert prob_zero_in_stratum(100, 50, 100) == 0.0


def test_prob_zero_matches_exact_hypergeometric_small_case():
    # N=10, n=2, M=3 -> C(7,2)/C(10,2) = 21/45
    assert prob_zero_in_stratum(10, 2, 3) == pytest.approx(21 / 45)


def test_prob_zero_decreases_in_M():
    ps = [prob_zero_in_stratum(10_000, 100, m) for m in (0, 10, 100, 1000)]
    assert ps == sorted(ps, reverse=True)
    assert all(0.0 <= p <= 1.0 for p in ps)


def test_observation_probability_decreases_in_M():
    ps = [observation_probability(STRATA, m) for m in (0, 100, 1000, 10_000)]
    assert ps == sorted(ps, reverse=True)
    assert ps[0] == pytest.approx(1.0)


def test_max_consistent_M_is_large_enough_to_matter():
    """데이터가 배제할 수 있는 하한이 추정 양성(97)보다 훨씬 크다 — 이것이 핵심."""
    m = max_consistent_M(STRATA, alpha=0.05)
    assert m > 10_000, f"기각 경계가 {m:.0f} — 데이터가 예상보다 많이 제약한다"
    # 경계 근처에서 실제로 alpha 를 가른다
    assert observation_probability(STRATA, m * 0.99) >= 0.05
    assert observation_probability(STRATA, m * 1.05) < 0.05


def test_recall_is_monotone_decreasing_in_M():
    rs = [recall_under_hypothesis(55.0, 97.0, m) for m in (0, 100, 1000, 10_000)]
    assert rs == sorted(rs, reverse=True)
    assert rs[0] == pytest.approx(55.0 / 97.0)


def test_recall_numerator_unaffected_by_hypothesis():
    """임계값 위에서 잡은 양성은 하위 가정과 무관하다."""
    assert recall_under_hypothesis(55.0, 97.0, 0) * 97.0 == pytest.approx(55.0)
    assert recall_under_hypothesis(55.0, 97.0, 903) * 1000.0 == pytest.approx(55.0)


def test_sensitivity_table_shape_and_flags():
    df = sensitivity_table(STRATA, tp=55.0, positives_measured=97.0)
    assert set(df.columns) == {"M", "p_observe_zero", "rejected_at_alpha", "recall"}
    assert not bool(df.loc[df.M == 0, "rejected_at_alpha"].iloc[0])
    assert list(df["recall"]) == sorted(df["recall"], reverse=True)


def test_name_collision_finds_planted_duplicate():
    names = ["미적분학", "선형대수", "미적분학", "물리학"]
    pairs = [(0, 1), (0, 2), (1, 3)]
    sims = [0.55, 0.30, 0.10]
    hits = name_collision_candidates(names, pairs, sims, max_sim=0.6)
    assert hits == [(0, 2, 0.30)], "같은 이름·낮은 유사도 쌍을 잡아야 한다"


def test_name_collision_ignores_pairs_above_threshold():
    names = ["미적분학", "미적분학"]
    assert name_collision_candidates(names, [(0, 1)], [0.95], max_sim=0.6) == []


def test_name_collision_ignores_blank_names():
    assert name_collision_candidates(["", ""], [(0, 1)], [0.1], max_sim=0.6) == []
