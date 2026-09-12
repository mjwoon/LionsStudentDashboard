from experiment.kappa import cohen_kappa, confusion_2x2


def test_perfect_agreement():
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0


def test_known_value():
    a = [1, 1, 0, 0, 1, 0]
    b = [1, 0, 0, 0, 1, 1]
    k = cohen_kappa(a, b)
    assert abs(k - 0.3333333) < 1e-6


def test_confusion_counts():
    c = confusion_2x2([1, 1, 0], [1, 0, 0])
    assert c == {"n11": 1, "n10": 1, "n01": 0, "n00": 1}
