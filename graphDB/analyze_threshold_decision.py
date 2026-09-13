r"""RQ1 후속 분석 — 비용 민감 임계값 곡선과 t* 안정성.

RQ1 본 실험은 t\* 를 '가중 F1 최대' 한 점으로 보고했다. 이 스크립트는 그 두
약점을 각각 측정치로 바꾼다.

1. **비용 민감 임계값** — F1 은 오탐·미탐을 같은 무게로 보지만 이 도메인은
   비대칭이다. 비용비 lam = c_FP/c_FN 에 대한 t\*(lam) 프런티어를 낸다.
2. **t\* 안정성** — 부트스트랩 t\* 표본의 산포(sd·CV·IQR·최빈값)를 낸다.
   넓은 CI 와 평탄한 F1 고원이 '추정 실패'가 아니라 희소 양성 조건의
   측정된 성질임을 보인다.

SBERT 재계산 없이 `pairs_labeled.csv`(쌍별 sim·층·가중치)와 기존 LLM 레이블만
읽는다. 없으면 `experiment_rq1.py` 를 먼저 실행해 생성한다.

사용법:
    uv run python analyze_threshold_decision.py \
        --pairs results/rq1/pairs_labeled.csv \
        --results results/rq1 --out results/rq1_decision
"""
from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from experiment.pairs import SampledPair  # noqa: E402
from experiment.metrics import sweep, best_threshold  # noqa: E402
from experiment.bootstrap import bootstrap_curves  # noqa: E402
from experiment.decision import cost_curve, tstar_distribution  # noqa: E402
from experiment.plotting import use_korean_font  # noqa: E402

# 오탐이 미탐보다 몇 배 비싼가. 로그 격자로 훑는다.
LAMBDAS = [0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 25.0, 50.0, 100.0]


def load_sample(pairs_csv: str) -> list[SampledPair]:
    df = pd.read_csv(pairs_csv)
    need = {"pair_id", "i", "j", "sim", "bin_idx", "weight"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"{pairs_csv}: 열 부족 {sorted(missing)}")
    return [SampledPair(int(r.pair_id), int(r.i), int(r.j),
                        float(r.sim), int(r.bin_idx), float(r.weight))
            for r in df.itertuples()]


def load_gold(results_dir: str) -> dict[int, int]:
    """gpt-4o 2회 독립 실행의 보수적 AND (= RQ1 골드)."""
    p1 = pd.read_csv(f"{results_dir}/llm_labels_pass1.csv").set_index("pair_id").label
    p2 = pd.read_csv(f"{results_dir}/llm_labels_pass2.csv").set_index("pair_id").label
    return {int(k): int(v) for k, v in ((p1 == 1) & (p2 == 1)).astype(int).items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="results/rq1/pairs_labeled.csv")
    ap.add_argument("--results", default="results/rq1", help="LLM 레이블이 있는 디렉터리")
    ap.add_argument("--out", default="results/rq1_decision")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    sample = load_sample(args.pairs)
    gold = load_gold(args.results)
    missing = [sp.pair_id for sp in sample if sp.pair_id not in gold]
    if missing:
        raise SystemExit(f"레이블 없는 pair_id {len(missing)}건: {missing[:10]}")

    thresholds = np.arange(0.30, 1.001, 0.01)
    base = sweep(sample, gold, thresholds)
    t_f1 = best_threshold(base)

    # --- 1. 비용 민감 임계값 --------------------------------------------
    cc = cost_curve(sample, gold, thresholds, LAMBDAS)
    cc.to_csv(f"{args.out}/cost_curve.csv", index=False)

    # --- 2. t* 안정성 ---------------------------------------------------
    boot = bootstrap_curves(sample, gold, thresholds,
                            n_boot=args.n_boot, seed=args.seed)
    dist = tstar_distribution(boot["tstar"])
    pd.DataFrame({"tstar": boot["tstar"]}).to_csv(
        f"{args.out}/tstar_bootstrap.csv", index=False)

    summary = {"tstar_f1": t_f1, "n_boot": args.n_boot,
               "tstar_distribution": dist,
               "cost_curve": cc.to_dict("records")}
    json.dump(summary, open(f"{args.out}/summary.json", "w"),
              ensure_ascii=False, indent=2)

    # --- 그림 -----------------------------------------------------------
    use_korean_font()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
    a1.semilogx(cc["lam"], cc["tstar"], "o-", color="#2c6fbb")
    # 로그축 기본 라벨은 10^{-1} 형태의 mathtext 라 한글 폰트에서 마이너스가 깨진다.
    # 비용비는 값 자체를 읽는 편이 낫기도 해서 눈금을 직접 지정한다.
    a1.set_xticks(list(cc["lam"]))
    a1.set_xticklabels([f"{v:g}" for v in cc["lam"]], fontsize=8)
    a1.minorticks_off()
    a1.axhline(t_f1, color="gray", ls="--", alpha=.7,
               label=f"argmax-F1 t*={t_f1:.2f}")
    a1.set_xlabel("비용비 λ = c_FP / c_FN  (오탐이 미탐보다 몇 배 비싼가)")
    a1.set_ylabel("비용 최적 임계값 t*(λ)")
    a1.set_title("비용 민감 임계값 프런티어")
    a1.legend(); a1.grid(alpha=.3)

    lo_x = max(0.30, dist["min"] - 0.04)
    hi_x = min(1.00, dist["max"] + 0.04)
    a2.hist(boot["tstar"], bins=np.arange(lo_x, hi_x + 0.01, 0.01),
            color="#2c6fbb", alpha=.85)
    a2.set_xlim(lo_x, hi_x)
    a2.axvline(dist["median"], color="black", ls="-", label=f"중앙값 {dist['median']:.2f}")
    a2.axvspan(dist["ci95"][0], dist["ci95"][1], color="orange", alpha=.18,
               label=f"95% CI [{dist['ci95'][0]:.2f}, {dist['ci95'][1]:.2f}]")
    a2.set_xlabel("부트스트랩 t*")
    a2.set_ylabel("빈도")
    a2.set_title(f"t* 분포 — 최빈값 {dist['mode']:.2f} ({dist['mode_share']*100:.0f}%), CV {dist['cv']:.3f}")
    a2.legend(); a2.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(f"{args.out}/threshold_decision.png", dpi=150)
    plt.close(fig)

    with open(f"{args.out}/summary.md", "w") as f:
        f.write("# RQ1 후속 — 비용 민감 임계값 · t* 안정성\n\n")
        f.write(f"- argmax-F1 임계값: **{t_f1:.2f}**\n")
        f.write(f"- 부트스트랩 {args.n_boot}회 t* : 중앙값 {dist['median']:.2f}, "
                f"평균 {dist['mean']:.3f}, sd {dist['sd']:.3f}, "
                f"**CV {dist['cv']:.3f}**, IQR {dist['iqr']:.2f}, "
                f"최빈값 {dist['mode']:.2f}({dist['mode_share']*100:.1f}%)\n")
        f.write(f"- t* 95% CI: [{dist['ci95'][0]:.2f}, {dist['ci95'][1]:.2f}]"
                f" / 범위 [{dist['min']:.2f}, {dist['max']:.2f}]\n\n")
        f.write("## 비용비별 최적 임계값\n\n")
        f.write("| lambda | t* | P | R | F1 |\n|---:|---:|---:|---:|---:|\n")
        for r in cc.itertuples():
            f.write(f"| {r.lam:g} | {r.tstar:.2f} | {r.precision:.3f} "
                    f"| {r.recall:.3f} | {r.f1:.3f} |\n")

    print(json.dumps({"tstar_f1": t_f1, "tstar_distribution": dist},
                     ensure_ascii=False, indent=2))
    print("\n비용비별 최적 임계값:")
    print(cc[["lam", "tstar", "precision", "recall", "f1"]].to_string(
        index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\n-> {args.out}/")


if __name__ == "__main__":
    main()
