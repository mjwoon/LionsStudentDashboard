import numpy as np
from experiment.pairs import SampledPair
from experiment.bootstrap import bootstrap_curves


def _sample():
    return [SampledPair(i, 0, i + 1, 0.5 + 0.05 * i, i % 2, 2.0) for i in range(10)]


def test_bootstrap_shapes_and_bounds():
    labels = {i: (1 if i % 2 else 0) for i in range(10)}
    th = np.arange(0.30, 1.001, 0.01)
    out = bootstrap_curves(_sample(), labels, th, n_boot=50, seed=42)
    assert out["f1_lo"].shape == th.shape
    assert np.all(out["f1_lo"] <= out["f1_hi"] + 1e-9)
    assert out["tstar"].shape == (50,)
    # 결정성
    out2 = bootstrap_curves(_sample(), labels, th, n_boot=50, seed=42)
    assert np.allclose(out["f1_lo"], out2["f1_lo"])
