import numpy as np
from experiment.pairs import SampledPair
from experiment.metrics import weighted_confusion, prf, sweep, best_threshold, pr_auc


def _sample():
    # 두 층: 층0 weight=2, 층1 weight=5
    return [
        SampledPair(0, 0, 1, 0.40, 0, 2.0),  # label 0
        SampledPair(1, 0, 2, 0.72, 0, 2.0),  # label 1
        SampledPair(2, 0, 3, 0.85, 1, 5.0),  # label 1
        SampledPair(3, 0, 4, 0.90, 1, 5.0),  # label 0
    ]


def test_weighted_confusion_matches_bin_formula():
    labels = {0: 0, 1: 1, 2: 1, 3: 0}
    tp, fp, fn = weighted_confusion(_sample(), labels, t=0.70)
    # sim>=0.70: pairs 1,2,3. TP=1*2 + 1*5 =7 ; FP=pair3 -> 0*5=5 ; FN=0
    assert (tp, fp, fn) == (7.0, 5.0, 0.0)


def test_prf_zero_safe():
    assert prf(0, 0, 0) == (0.0, 0.0, 0.0)


def test_sweep_and_best_threshold():
    labels = {0: 0, 1: 1, 2: 1, 3: 0}
    df = sweep(_sample(), labels, np.arange(0.30, 1.001, 0.01))
    assert set(df.columns) >= {"threshold", "precision", "recall", "f1"}
    t = best_threshold(df)
    assert 0.30 <= t <= 1.0
    assert 0.0 <= pr_auc(df) <= 1.0
