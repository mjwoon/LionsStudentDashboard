import numpy as np
from experiment.sampling import bin_index, stratified_sample, BINS


def test_bin_index_boundaries():
    assert bin_index(0.0) == 0
    assert bin_index(0.49) == 0
    assert bin_index(0.5) == 1
    assert bin_index(0.75) == 3
    assert bin_index(1.0) == 5


def test_stratified_sample_counts_and_weights_and_determinism():
    # 각 구간에 정확히 200개씩 모집단 배치
    sims = np.concatenate([np.full(200, c + 0.01) for c in
                           (0.0, 0.5, 0.6, 0.7, 0.8, 0.9)])
    pairs = np.stack([np.arange(len(sims)), np.arange(len(sims)) + 1], axis=1)
    per_bin = [100, 60, 60, 60, 60, 60]
    sample, N_k = stratified_sample(pairs, sims, per_bin, seed=42)
    assert N_k == [200, 200, 200, 200, 200, 200]
    counts = [sum(1 for s in sample if s.bin_idx == b) for b in range(6)]
    assert counts == per_bin
    # weight = N_k / n_k
    w0 = next(s.weight for s in sample if s.bin_idx == 0)
    assert abs(w0 - 200 / 100) < 1e-9
    # 결정성: 같은 시드 → 같은 pair 집합
    sample2, _ = stratified_sample(pairs, sims, per_bin, seed=42)
    assert [s.i for s in sample] == [s.i for s in sample2]
