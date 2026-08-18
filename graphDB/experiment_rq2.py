"""RQ2: 임계값 변화의 하위 시스템 영향 (오프라인 전면 재계산).

루트 3.12 환경에서 실행한다(backend `services` + `lions_core` 필요).
유사도는 build_similarity_lookup.py 가 미리 덤프한 lookup 을 로드한다(sbert 불필요).
"""
from __future__ import annotations

import os
import sys

# backend 를 graphDB 보다 sys.path 앞에 둔다(동명 `config` 모듈 충돌 회피).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_ROOT, "backend")):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

import argparse  # noqa: E402
import json  # noqa: E402

import pandas as pd  # noqa: E402

# matplotlib 은 graphDB 전용 의존성 → 루트 환경엔 없을 수 있다. 없으면 플롯만 생략.
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_PLT = True
except ImportError:
    _HAS_PLT = False

from lions_core.models import Student, Department  # noqa: E402
from lions_core.constants import LIONS_COLLEGE_ID  # noqa: E402
from experiment.similarity_lookup import load_lookup, make_similarity_fn  # noqa: E402
from experiment.injected_eval import InjectedEvaluationService  # noqa: E402
from experiment.seeding import seed_sqlite  # noqa: E402
from experiment.impact_metrics import (  # noqa: E402
    spearman_vs_baseline, top1_change_rate, grade_migration,
)


def _evaluate_all(db, sim_fn, threshold, max_students=0):
    svc = InjectedEvaluationService(db, sim_fn, threshold)
    students = db.query(Student).all()
    if max_students:
        students = students[:max_students]
    depts = [d.id for d in db.query(Department).all() if d.id > LIONS_COLLEGE_ID]
    rows = []
    for st in students:
        sid = st.student_id
        year = svc.get_admission_year_from_student_id(str(sid))
        for did in depts:
            try:
                r = svc.evaluate_student(sid, did, year, save_to_db=False)
            except Exception:
                continue
            rows.append({"student_id": sid, "department_id": did,
                         "overall_score": r["overall_score"], "grade": r["grade"]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=_ROOT)
    ap.add_argument("--lookup", default="results/rq2/similarity_lookup.json")
    ap.add_argument("--out", default="results/rq2")
    ap.add_argument("--tstar", type=float, required=True, help="RQ1에서 얻은 t*")
    ap.add_argument("--db", default="results/rq2/seed.db")
    ap.add_argument("--max-students", type=int, default=0, help="스모크용 학생 수 제한(0=전체)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    lut = load_lookup(args.lookup)
    sim_fn = make_similarity_fn(lut)

    if os.path.exists(args.db):
        os.remove(args.db)
    db = seed_sqlite(args.db, args.repo_root)

    thresholds = sorted({0.6, 0.7, 0.8, round(args.tstar, 2)})
    evals = {}
    for t in thresholds:
        e = _evaluate_all(db, sim_fn, t, max_students=args.max_students)
        e.to_csv(f"{args.out}/evaluations_{t}.csv", index=False)
        evals[t] = e

    base = evals[0.8]  # 현행 실효값 기준선
    summary = {"thresholds": thresholds,
               "n_rows_per_threshold": {t: int(len(evals[t])) for t in thresholds},
               "n_additional_relations": {t: int(sum(1 for v in lut.values() if v >= t))
                                          for t in thresholds}}
    stab_rows = []
    for t in thresholds:
        rho = spearman_vs_baseline(evals[t], base)
        stab_rows.append({"threshold": t,
                          "spearman_mean": float(rho.mean()) if len(rho) else 1.0,
                          "spearman_min": float(rho.min()) if len(rho) else 1.0,
                          "top1_change_rate": top1_change_rate(evals[t], base)})
        grade_migration(evals[t], base).to_csv(f"{args.out}/grade_migration_{t}.csv")
    pd.DataFrame(stab_rows).to_csv(f"{args.out}/ranking_stability.csv", index=False)

    if _HAS_PLT:
        fig, ax = plt.subplots(figsize=(8, 5))
        for t in thresholds:
            ax.hist(evals[t]["overall_score"], bins=40, histtype="step", label=f"t={t}")
        ax.set_xlabel("overall_score")
        ax.set_ylabel("frequency")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f"{args.out}/score_shift.png", dpi=150)
        plt.close(fig)
    else:
        summary["plot_skipped"] = "matplotlib 미설치(루트 env) — score_shift.png 생략"

    json.dump(summary, open(f"{args.out}/summary.json", "w"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    db.close()


if __name__ == "__main__":
    main()
