import pandas as pd
from experiment.pairs import SampledPair
from experiment.tfidf_labeler import tfidf_labels


def test_identical_names_labeled_positive():
    df = pd.DataFrame({"교과목 이름": ["데이터구조", "데이터구조론", "미술사"],
                       "교과목개요": ["", "", ""]})
    sample = [SampledPair(0, 0, 1, 0.9, 5, 1.0), SampledPair(1, 0, 2, 0.1, 0, 1.0)]
    labels = tfidf_labels(df, sample, threshold=0.30)
    assert labels[0] == 1   # 이름 거의 동일
    assert labels[1] == 0   # 무관
