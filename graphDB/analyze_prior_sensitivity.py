r"""RQ1 후속 — 재현율이 데이터가 아니라 전제에 의해 정해지는 범위를 측정한다.

논문의 가장 큰 한계는 재현율이 "유사도 0.6 미만에 대체 인정 가능한 쌍이 없다"는
**미검증 전제** 위에 있다는 점이다. 계획서는 표본 증량을 대응책으로 뒀지만 필요
표본이 34,000건이라 현실성이 없다.

여기서는 증량 대신 두 가지를 한다.

1. **전제가 데이터에 의해 얼마나 제약되는지 정확히 계산한다.** 하위 양성 수 M 을
   가정했을 때 실제 관측(0/100, 0/60)이 나올 결합 확률을 초기하분포로 구하고,
   그때의 재현율을 함께 보고한다. 기각되지 않는 M 의 범위가 넓다면 그 구간에서
   재현율은 측정값이 아니라 가정값이다.
2. **무작위 표본이 놓쳤을 곳을 직접 뒤진다.** 이름이 똑같은데 유사도가 낮은 쌍은
   유사도 척도의 명백한 실패 사례다. 그런 쌍이 없다는 것은 무작위 0건보다
   훨씬 강한 증거이며, 추가 레이블링 비용이 들지 않는다.

사용법:
    uv run python analyze_prior_sensitivity.py
"""
from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from experiment.metrics import sweep, weighted_confusion  # noqa: E402
from experiment.plotting import use_korean_font  # noqa: E402
from experiment.prior import (  # noqa: E402
    max_consistent_M, name_collision_candidates, observation_probability,
    recall_under_hypothesis, sensitivity_table,
)
from experiment.rq1_data import load_sample, load_gold, require_labels  # noqa: E402

GRID = [0, 10, 50, 100, 500, 1_000, 5_000, 10_000, 20_000, 33_000, 50_000]
ALPHAS = [0.10, 0.05, 0.01]
LOW_BAND_MAX = 0.6


def _rule_of_three(strata):
    """계획서가 쓴 보수적 상한 — 층마다 3/n 을 따로 잡아 더한다."""
    return sum(N * (3.0 / n) for N, n in strata)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="results/rq1/pairs_labeled.csv")
    ap.add_argument("--results", default="results/rq1")
    ap.add_argument("--csv", default="course_all_aggregated.csv")
    ap.add_argument("--out", default="results/rq1_prior")
    ap.add_argument("--tstar", type=float, default=0.70)
    ap.add_argument("--skip-screen", action="store_true",
                    help="이름 충돌 탐색 생략(SBERT 재계산 불필요해짐)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    sample = load_sample(args.pairs)
    gold = load_gold(args.results)
    require_labels(sample, gold)

    strata_json = json.load(open(f"{args.results}/strata.json"))
    N_k = strata_json["N_k"]

    # 양성이 0건 관측된 층만 추린다(= 유사도 0.6 미만의 두 층)
    zero_strata = []
    for b in sorted({sp.bin_idx for sp in sample}):
        members = [sp for sp in sample if sp.bin_idx == b]
        if sum(gold[sp.pair_id] for sp in members) == 0:
            zero_strata.append((int(N_k[b]), len(members)))

    # 측정된 영역(>=0.6)의 가중 양성 추정과 t* 에서의 TP
    pos_measured = sum(sp.weight for sp in sample if gold[sp.pair_id] == 1)
    tp, _, _ = weighted_confusion(sample, gold, args.tstar)

    table = sensitivity_table(zero_strata, tp=tp, positives_measured=pos_measured,
                              grid=GRID)
    table.to_csv(f"{args.out}/recall_sensitivity.csv", index=False)

    bounds = {f"alpha={a}": max_consistent_M(zero_strata, alpha=a) for a in ALPHAS}
    r3 = _rule_of_three(zero_strata)

    screen = None
    if not args.skip_screen:
        from similarity_engine import load_course_data
        from experiment.pairs import valid_pair_indices, compute_hybrid_similarity
        df = load_course_data(args.csv)
        pairs = valid_pair_indices(df)
        simm = compute_hybrid_similarity(df)
        sims = np.array([simm[i][j] for i, j in pairs])
        names = df["교과목 이름"].fillna("").astype(str).tolist()
        hits = name_collision_candidates(names, pairs, sims, max_sim=LOW_BAND_MAX)
        screen = {
            "n_pairs_below": int((sims < LOW_BAND_MAX).sum()),
            "n_identical_name": len(hits),
            "examples": [{"i": i, "j": j, "sim": s, "name": names[i]}
                         for i, j, s in hits[:20]],
            "n_outside_strata": int(len(sims) - sum(N_k)),
            "n_negative_sim": int((sims < 0).sum()),
        }

    summary = {
        "tstar": args.tstar,
        "zero_strata": [{"N": N, "n": n} for N, n in zero_strata],
        "positives_measured_weighted": pos_measured,
        "tp_at_tstar": tp,
        "recall_reported": recall_under_hypothesis(tp, pos_measured, 0.0),
        "max_consistent_M": bounds,
        "rule_of_three_bound": r3,
        "sensitivity": table.to_dict("records"),
        "name_collision_screen": screen,
    }
    json.dump(summary, open(f"{args.out}/summary.json", "w"),
              ensure_ascii=False, indent=2, default=float)

    # --- 그림 ---
    use_korean_font()
    fig, ax = plt.subplots(figsize=(9, 5))
    grid = np.unique(np.concatenate([
        np.linspace(0, 2_000, 300), np.linspace(2_000, 60_000, 300)]))
    probs = [observation_probability(zero_strata, m) for m in grid]
    recs = [recall_under_hypothesis(tp, pos_measured, m) for m in grid]
    ax.plot(grid, recs, lw=2, color="#2c6fbb", label="재현율 (좌축)")
    ax.set_xscale("symlog", linthresh=100)
    ax.set_xlabel("가정한 하위 구간(유사도<0.6) 양성 수 M")
    ax.set_ylabel("t*=%.2f 에서의 재현율" % args.tstar)
    ax.set_ylim(0, 0.65)
    ax.grid(alpha=.3)
    m95 = bounds["alpha=0.05"]
    ax.axvspan(0, m95, color="orange", alpha=.13,
               label=f"관측과 양립 (M ≤ {m95:,.0f}, 5%)")
    ax.axvline(m95, color="#c62828", ls="--", lw=1.3)
    ax2 = ax.twinx()
    ax2.plot(grid, probs, lw=1.4, ls=":", color="gray",
             label="0/160 이 관측될 확률 (우축)")
    ax2.set_ylabel("P(관측 = 0건)")
    ax2.set_ylim(0, 1.02)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9)
    ax.set_title("재현율은 M 이 정한다 — 그리고 데이터는 M 을 거의 제약하지 못한다")
    fig.tight_layout()
    fig.savefig(f"{args.out}/recall_sensitivity.png", dpi=150)
    plt.close(fig)

    with open(f"{args.out}/summary.md", "w") as f:
        f.write("# RQ1 후속 — 재현율 민감도와 검정력\n\n")
        f.write(f"양성 0건 관측 층: {[(N, n) for N, n in zero_strata]}  "
                f"(유사도 < {LOW_BAND_MAX})\n\n")
        f.write(f"측정 영역(≥0.6) 가중 양성 **{pos_measured:.0f}** · "
                f"t\\*={args.tstar:.2f} 에서 TP **{tp:.1f}** · "
                f"보고 재현율 **{summary['recall_reported']:.3f}**\n\n")
        f.write("## M 가정별 관측 확률과 재현율\n\n")
        f.write("| M | P(0/160 관측) | 5%에서 기각 | 재현율 |\n|---:|---:|:--:|---:|\n")
        for r in summary["sensitivity"]:
            f.write(f"| {r['M']:,.0f} | {r['p_observe_zero']:.3f} | "
                    f"{'예' if r['rejected_at_alpha'] else '아니오'} | "
                    f"{r['recall']:.3f} |\n")
        f.write("\n## 데이터가 배제할 수 있는 범위\n\n")
        for k, v in bounds.items():
            f.write(f"- {k}: M ≤ **{v:,.0f}**\n")
        f.write(f"\n계획서의 rule of three 상한(층별 3/n 합산): {r3:,.0f} "
                f"→ 결합 초기하로 계산하면 **{bounds['alpha=0.05']:,.0f}** 로 좁아진다.\n")
        if screen:
            f.write(f"\n## 이름 충돌 탐색 (비용 0)\n\n"
                    f"유사도 < {LOW_BAND_MAX} 인 쌍 {screen['n_pairs_below']:,} 중 "
                    f"**교과목명이 완전히 같은 쌍은 {screen['n_identical_name']}건**이다.\n\n"
                    f"참고: 유효 쌍 중 {screen['n_outside_strata']:,}건이 층 경계 밖"
                    f"(유사도 음수 {screen['n_negative_sim']:,}건)이라 "
                    f"모집단·표본 양쪽에서 빠져 있다. 전부 음의 유사도이므로 "
                    f"대체 인정 후보가 아니며 누락 방향은 보수적이다.\n")

    print(json.dumps({k: v for k, v in summary.items() if k != "sensitivity"},
                     ensure_ascii=False, indent=2, default=float))
    print("\n" + table.to_string(index=False))
    print(f"\n-> {args.out}/")


if __name__ == "__main__":
    main()
