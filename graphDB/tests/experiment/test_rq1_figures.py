"""RQ1 그림 생성과 저장된 LLM 레이블 재사용.

논문 그림이 코드로 재현되지 않던 적이 있어(코드는 F1 하나만 그리고
pr_curve.png 는 아예 만들지 않았다) 산출을 테스트로 고정한다.
"""
import numpy as np
import pandas as pd
import pytest

import experiment_rq1 as rq1
from experiment.plotting import use_korean_font
from experiment.pairs import SampledPair


@pytest.fixture(autouse=True)
def _korean_font():
    """그림에 한글 라벨이 들어가므로 폰트를 확정한 뒤 그린다."""
    use_korean_font(force=True)

THRESHOLDS = np.arange(0.30, 1.001, 0.01)


def _curves():
    sample = [
        SampledPair(0, 0, 1, 0.40, 0, 2.0),
        SampledPair(1, 0, 2, 0.72, 0, 2.0),
        SampledPair(2, 0, 3, 0.85, 1, 5.0),
        SampledPair(3, 0, 4, 0.90, 1, 5.0),
    ]
    labels = {0: 0, 1: 1, 2: 1, 3: 0}
    from experiment.metrics import sweep, best_threshold
    df = sweep(sample, labels, THRESHOLDS)
    return {gt: {"sweep": df, "tstar": best_threshold(df), "ci": [0.66, 0.79]}
            for gt in ("llm", "tfidf")}


def test_plot_f1_threshold_writes_png(tmp_path):
    out = tmp_path / "f1.png"
    rq1.plot_f1_threshold(_curves(), "llm", 1000, str(out))
    assert out.exists() and out.stat().st_size > 5000


def test_plot_pr_curve_writes_png(tmp_path):
    out = tmp_path / "pr.png"
    rq1.plot_pr_curve(_curves(), "llm", str(out))
    assert out.exists() and out.stat().st_size > 5000


def test_plot_works_with_tfidf_only_primary(tmp_path):
    """--no-llm 실행에서도 그림이 나와야 한다."""
    c = _curves()
    del c["llm"]
    rq1.plot_f1_threshold(c, "tfidf", 50, str(tmp_path / "f1.png"))
    rq1.plot_pr_curve(c, "tfidf", str(tmp_path / "pr.png"))
    assert (tmp_path / "f1.png").exists() and (tmp_path / "pr.png").exists()


def test_read_labels_roundtrip(tmp_path):
    p = tmp_path / "labels.csv"
    pd.DataFrame([{"pair_id": 3, "label": 1}, {"pair_id": 7, "label": 0}]).to_csv(p, index=False)
    assert rq1._read_labels(str(p)) == {3: 1, 7: 0}


def test_adjudicate_is_conservative_and():
    p1 = {0: 1, 1: 1, 2: 0, 3: 0}
    p2 = {0: 1, 1: 0, 2: 1, 3: 0}
    # 2회 모두 '인정'일 때만 양성
    assert rq1._adjudicate(p1, p2) == {0: 1, 1: 0, 2: 0, 3: 0}


def test_baseline_threshold_is_documented_as_comparison_only():
    """0.80 은 코드의 설정값이 아니라 비교 기준(보수적 관행값)이다."""
    assert rq1.BASELINE_T == 0.80
