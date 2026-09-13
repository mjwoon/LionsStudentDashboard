"""RQ1 산출물 로더 — 잘못된 입력을 조용히 넘기지 않는다."""
import pandas as pd
import pytest

from experiment.pairs import SampledPair
from experiment.rq1_data import load_sample, load_gold, require_labels


def test_load_sample_roundtrip(tmp_path):
    p = tmp_path / "pairs.csv"
    pd.DataFrame([{"pair_id": 0, "i": 1, "j": 2, "sim": 0.8, "bin_idx": 4,
                   "weight": 1.0}]).to_csv(p, index=False)
    s = load_sample(str(p))
    assert len(s) == 1 and s[0].sim == 0.8 and s[0].bin_idx == 4


def test_load_sample_reports_missing_columns(tmp_path):
    p = tmp_path / "bad.csv"
    pd.DataFrame([{"pair_id": 0, "sim": 0.8}]).to_csv(p, index=False)
    with pytest.raises(SystemExit, match="열 부족"):
        load_sample(str(p))


def test_load_gold_is_conservative_and(tmp_path):
    for tag, labels in (("pass1", [1, 1, 0]), ("pass2", [1, 0, 1])):
        pd.DataFrame({"pair_id": [0, 1, 2], "label": labels}).to_csv(
            tmp_path / f"llm_labels_{tag}.csv", index=False)
    assert load_gold(str(tmp_path)) == {0: 1, 1: 0, 2: 0}


def test_require_labels_raises_on_gap():
    sample = [SampledPair(7, 0, 1, 0.8, 4, 1.0)]
    with pytest.raises(SystemExit, match="레이블 없는"):
        require_labels(sample, {0: 1})
    require_labels(sample, {7: 1})   # 있으면 통과
