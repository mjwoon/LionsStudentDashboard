import numpy as np
import pandas as pd
from experiment.similarity_lookup import (
    build_lookup, make_similarity_fn, save_lookup, load_lookup,
)


def test_lookup_filters_and_is_symmetric():
    df = pd.DataFrame({"교과목 이름": ["a", "b", "c"], "교과목개요": ["", "", ""],
                       "학수번호": ["C1", "C2", "C3"]})
    sim = np.array([[1.0, 0.9, 0.4], [0.9, 1.0, 0.65], [0.4, 0.65, 1.0]])
    lut = build_lookup(df, sim, min_keep=0.6)
    assert ("C1", "C2") in lut and ("C2", "C3") in lut
    assert ("C1", "C3") not in lut  # 0.4 < 0.6 제외
    fn = make_similarity_fn(lut)
    assert fn("C2", "C1") == 0.9 and fn("C1", "C3") == 0.0


def test_save_load_roundtrip(tmp_path):
    lut = {("A", "B"): 0.9, ("B", "C"): 0.65}
    p = tmp_path / "lut.json"
    save_lookup(lut, str(p))
    back = load_lookup(str(p))
    assert back == lut
    fn = make_similarity_fn(back)
    assert fn("B", "A") == 0.9
