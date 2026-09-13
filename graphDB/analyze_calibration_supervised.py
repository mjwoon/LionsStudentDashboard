r"""RQ1 후속 — 유사도 보정(②)과 지도학습 비교(③).

임계값 하나로 판정하는 현행 방식에 대한 두 가지 대안을 측정한다.

**② 보정.** 유사도를 등위 보존 회귀로 P(대체 인정)로 옮기면 임계값이 비용에서
유도된다(P >= lam/(1+lam)). 스윕에서 비용을 직접 최소화한 `decision.cost_curve` 와
독립인 경로이므로 두 결과가 일치하면 상호 검증이 된다.

**③ 지도학습.** Kim 등(EDM 2025)은 임계값 방식을 배제하고 임베딩 차이 벡터에
분류기를 학습시켰다. 이 레이블 예산(335쌍·양성 59)에서 그 선택지가 실제로
존재하는지 확인한다. 임계값도 학습 폴드에서 고르고 시험 폴드에 적용해 공정하게
비교하며, 평가는 모집단 가중으로 한다.

③ 은 SBERT 임베딩이 필요하다(`--skip-supervised` 로 생략 가능).

사용법:
    uv run python analyze_calibration_supervised.py
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

from experiment.calibration import (  # noqa: E402
    fit_isotonic, calibrated_threshold, cost_optimal_probability,
    weighted_brier, cross_val_probabilities,
)
from experiment.decision import cost_curve  # noqa: E402
from experiment.plotting import use_korean_font  # noqa: E402
from experiment.rq1_data import load_sample, load_gold, require_labels  # noqa: E402
from experiment.supervised import (  # noqa: E402
    oof_threshold_baseline, sweep_supervised, weighted_prf_from_preds,
)

LAMBDAS = [0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 100.0]
REPORT_SIMS = [0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


def _embeddings(csv_path: str, cache: str) -> np.ndarray:
    """과목별 SBERT 임베딩. 한 번 계산해 캐시한다."""
    if os.path.exists(cache):
        return np.load(cache)
    from similarity_engine import SimilarityEngine, load_course_data
    df = load_course_data(csv_path)
    df = df.copy()
    df["feature_text"] = df["교과목 이름"] + " " + df["교과목개요"].fillna("")
    emb = SimilarityEngine().create_embeddings(df, use_tfidf_weighting=True)
    np.save(cache, emb)
    return emb


def run_calibration(sample, gold, out):
    iso = fit_isotonic(sample, gold)
    curve = [{"sim": s, "p_substitutable": float(iso.predict([s])[0])}
             for s in REPORT_SIMS]

    thresholds = np.arange(0.30, 1.001, 0.01)
    emp = cost_curve(sample, gold, thresholds, LAMBDAS).set_index("lam")
    rows = []
    for lam in LAMBDAS:
        p_star = cost_optimal_probability(lam)
        t_cal = calibrated_threshold(iso, p_star)
        t_emp = float(emp.loc[lam, "tstar"])
        rows.append({"lam": lam, "p_star": p_star, "t_calibrated": t_cal,
                     "t_empirical": t_emp, "diff": t_cal - t_emp})
    agree = pd.DataFrame(rows)
    agree.to_csv(f"{out}/calibration_vs_empirical.csv", index=False)

    # out-of-fold 보정 품질 (상수 예측 기준선과 비교)
    oof = cross_val_probabilities(sample, gold, n_folds=5, seed=42)
    y = [gold[sp.pair_id] for sp in sample]
    w = [sp.weight for sp in sample]
    base = float(np.average(y, weights=w))
    brier_cal = weighted_brier([oof[sp.pair_id] for sp in sample], y, w)
    brier_base = weighted_brier([base] * len(sample), y, w)
    brier_raw = weighted_brier([sp.sim for sp in sample], y, w)

    return iso, {
        "curve": curve,
        "agreement": agree.to_dict("records"),
        "max_abs_diff": float(agree["diff"].abs().max()),
        "brier_oof_calibrated": brier_cal,
        "brier_constant_baseline": brier_base,
        "brier_raw_similarity": brier_raw,
        "weighted_base_rate": base,
    }


def run_supervised(sample, gold, emb, out, n_folds, seed):
    """지도학습 격자 전체 vs 폴드 내 선택 임계값.

    한 설정만 비교하면 기준선을 약하게 잡았다는 반론을 받으므로, 특징 3종 x
    모델 7종을 모두 돌려 지도학습의 최고 성적을 임계값과 맞붙인다.
    """
    grid = sweep_supervised(sample, gold, emb, n_folds=n_folds, seed=seed)
    grid.to_csv(f"{out}/supervised_grid.csv", index=False)
    best = grid.iloc[0]

    thr_preds, chosen = oof_threshold_baseline(
        sample, gold, np.arange(0.30, 1.001, 0.01), n_folds=n_folds, seed=seed)
    tp, tr_, tf = weighted_prf_from_preds(sample, gold, thr_preds)

    return {
        "grid": grid.to_dict("records"),
        "best_supervised": {
            "features": best["features"], "model": best["model"],
            "n_features": int(best["n_features"]),
            "precision": float(best["precision"]),
            "recall": float(best["recall"]), "f1": float(best["f1"]),
        },
        "threshold_baseline": {"precision": tp, "recall": tr_, "f1": tf,
                               "fold_thresholds": chosen},
        "f1_ratio_threshold_over_supervised": (
            float(tf / best["f1"]) if best["f1"] > 0 else None),
        "n_labeled": len(sample),
        "n_positive": int(sum(gold[sp.pair_id] for sp in sample)),
    }


def plot(iso, cal, out):
    use_korean_font()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
    grid = np.arange(0.3, 1.0005, 0.001)
    a1.plot(grid, iso.predict(grid), lw=2, color="#2c6fbb")
    for p in (0.5,):
        a1.axhline(p, color="gray", ls=":", lw=1)
    a1.axvline(0.70, color="#c62828", ls="--", lw=1.3, label="현행 0.70")
    a1.set_xlabel("하이브리드 유사도")
    a1.set_ylabel("P(대체 인정 가능)")
    a1.set_title("보정 곡선 — 유사도를 확률로")
    a1.set_ylim(0, 1)
    a1.legend(fontsize=9)
    a1.grid(alpha=.3)

    ag = pd.DataFrame(cal["agreement"])
    a2.plot(ag["t_empirical"], ag["t_calibrated"], "o", ms=8, color="#2c6fbb")
    lim = [0.6, 1.0]
    a2.plot(lim, lim, ls="--", color="gray", lw=1, label="완전 일치선")
    a2.set_xlim(*lim)
    a2.set_ylim(*lim)
    a2.set_xlabel("비용 최소화 실측 t*(λ)  [①]")
    a2.set_ylabel("보정 곡선 역산 t  [②]")
    a2.set_title(f"두 경로의 일치 (최대 차이 {cal['max_abs_diff']:.3f})")
    a2.legend(fontsize=9)
    a2.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(f"{out}/calibration_supervised.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="results/rq1/pairs_labeled.csv")
    ap.add_argument("--results", default="results/rq1")
    ap.add_argument("--csv", default="course_all_aggregated.csv")
    ap.add_argument("--out", default="results/rq1_calibration")
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-supervised", action="store_true",
                    help="SBERT 임베딩 계산을 생략(② 보정만)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    sample = load_sample(args.pairs)
    gold = load_gold(args.results)
    require_labels(sample, gold)

    iso, cal = run_calibration(sample, gold, args.out)
    summary = {"calibration": cal}

    if not args.skip_supervised:
        emb = _embeddings(args.csv, f"{args.results}/course_embeddings.npy")
        summary["supervised"] = run_supervised(
            sample, gold, emb, args.out, args.n_folds, args.seed)

    plot(iso, cal, args.out)
    json.dump(summary, open(f"{args.out}/summary.json", "w"),
              ensure_ascii=False, indent=2)

    with open(f"{args.out}/summary.md", "w") as f:
        f.write("# RQ1 후속 — 보정과 지도학습 비교\n\n## ② 유사도 보정\n\n")
        f.write("| 유사도 | P(대체 인정) |\n|---:|---:|\n")
        for r in cal["curve"]:
            f.write(f"| {r['sim']:.2f} | {r['p_substitutable']:.3f} |\n")
        f.write(f"\n가중 Brier — 보정(out-of-fold) **{cal['brier_oof_calibrated']:.5f}** / "
                f"상수 기준선 {cal['brier_constant_baseline']:.5f} / "
                f"원유사도 {cal['brier_raw_similarity']:.5f}\n\n")
        f.write("### 비용에서 유도한 임계값 vs 실측\n\n")
        f.write("| λ | P\\*=λ/(1+λ) | 보정 역산 t | 실측 t\\*(λ) | 차이 |\n")
        f.write("|---:|---:|---:|---:|---:|\n")
        for r in cal["agreement"]:
            f.write(f"| {r['lam']:g} | {r['p_star']:.3f} | {r['t_calibrated']:.3f} "
                    f"| {r['t_empirical']:.2f} | {r['diff']:+.3f} |\n")
        f.write(f"\n최대 절대 차이 **{cal['max_abs_diff']:.3f}**\n")
        if "supervised" in summary:
            sup = summary["supervised"]
            b, t = sup["best_supervised"], sup["threshold_baseline"]
            f.write(f"\n## ③ 지도학습 vs 임계값\n\n레이블 {sup['n_labeled']}쌍"
                    f"(양성 {sup['n_positive']}) · 층 내 {args.n_folds}겹 "
                    f"out-of-fold · 모집단 가중\n\n")
            f.write("| 방법 | P | R | F1 |\n|---|---:|---:|---:|\n")
            f.write(f"| 지도학습 최고 ({b['features']}, {b['model']}, "
                    f"{b['n_features']}d) | {b['precision']:.3f} | "
                    f"{b['recall']:.3f} | **{b['f1']:.3f}** |\n")
            f.write(f"| 임계값 (폴드 내 선택) | {t['precision']:.3f} | "
                    f"{t['recall']:.3f} | **{t['f1']:.3f}** |\n")
            f.write(f"\n임계값이 지도학습 최고 성적의 "
                    f"**{sup['f1_ratio_threshold_over_supervised']:.2f}배**\n\n")
            f.write(f"폴드별 선택 임계값: "
                    f"{[round(x, 2) for x in t['fold_thresholds']]}\n\n")
            f.write("### 격자 전체 (F1 내림차순)\n\n")
            f.write("| 특징 | 모델 | P | R | F1 |\n|---|---|---:|---:|---:|\n")
            for r in sup["grid"]:
                f.write(f"| {r['features']} | {r['model']} | {r['precision']:.3f} "
                        f"| {r['recall']:.3f} | {r['f1']:.3f} |\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=float))
    print(f"\n-> {args.out}/")


if __name__ == "__main__":
    main()
