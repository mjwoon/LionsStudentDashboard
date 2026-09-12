import pandas as pd
from experiment.impact_metrics import top1_change_rate, spearman_vs_baseline, grade_migration


def _df(scores):
    rows = []
    for sid, per_dept in scores.items():
        for did, sc in per_dept.items():
            rows.append({"student_id": sid, "department_id": did,
                         "overall_score": sc, "grade": "A" if sc >= 90 else "B"})
    return pd.DataFrame(rows)


def test_top1_change_rate():
    base = _df({1: {10: 95, 20: 80}, 2: {10: 70, 20: 75}})
    new = _df({1: {10: 95, 20: 80}, 2: {10: 88, 20: 75}})  # 학생2 top1 20→10
    assert top1_change_rate(new, base) == 0.5


def test_spearman_and_migration():
    base = _df({1: {10: 90, 20: 80, 30: 70}})
    new = _df({1: {10: 70, 20: 80, 30: 90}})   # 완전 역순 → ρ = -1
    rho = spearman_vs_baseline(new, base)
    assert abs(rho[1] + 1.0) < 1e-9
    mig = grade_migration(new, base)
    assert mig.values.sum() == 3
