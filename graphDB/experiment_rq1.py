"""RQ1: 대체 인정 최적 임계값 실험 (하이브리드 유사도 + LLM/TF-IDF GT)."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from similarity_engine import load_course_data  # noqa: E402
from experiment.pairs import valid_pair_indices, compute_hybrid_similarity  # noqa: E402
from experiment.sampling import stratified_sample  # noqa: E402
from experiment.tfidf_labeler import tfidf_labels  # noqa: E402
from experiment.llm_labeler import label_pairs  # noqa: E402
from experiment.kappa import cohen_kappa, confusion_2x2  # noqa: E402
from experiment.metrics import sweep, best_threshold, pr_auc  # noqa: E402
from experiment.bootstrap import bootstrap_curves  # noqa: E402
from experiment.plotting import use_korean_font  # noqa: E402

# 상위 3구간(≥0.7)은 모집단이 희박(실측 64/34/17)해 전수 레이블링한다.
# 큰 값 → stratified_sample 의 min(per_bin, N_k) 로 자동 전수.
CENSUS = 10**9
PER_BIN = [100, 60, 60, CENSUS, CENSUS, CENSUS]

THRESH_LO, THRESH_HI, THRESH_STEP = 0.30, 1.00, 0.01


def _make_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _read_labels(path: str) -> dict:
    """저장된 레이블 CSV(pair_id,label) → {pair_id: label}."""
    df = pd.read_csv(path)
    return {int(r.pair_id): int(r.label) for r in df.itertuples()}


def _finish_llm(results, sample, p1, p2, gold):
    ids = [sp.pair_id for sp in sample]
    results["llm"] = gold
    results["_inter_llm_kappa"] = cohen_kappa([p1[i] for i in ids], [p2[i] for i in ids])


def _adjudicate(p1: dict, p2: dict) -> dict:
    # 2회 불일치는 보수적으로 '인정 안 함'(0)으로 확정
    return {pid: (1 if p1[pid] == 1 and p2[pid] == 1 else 0) for pid in p1}


GT_LABEL = {"llm": "LLM 골드", "tfidf": "TF-IDF silver"}
GT_COLOR = {"llm": "#1f4e79", "tfidf": "#d2791e"}
BASELINE_T = 0.80  # 비교 기준(보수적 관행값). 코드의 설정값이 아니다.


def plot_f1_threshold(curves, primary, n_boot, path):
    """임계값별 P/R/F1 + t* 와 95% CI (주 정답지 기준)."""
    use_korean_font()
    c = curves[primary]
    df, t_star, ci = c["sweep"], c["tstar"], c["ci"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axvspan(ci[0], ci[1], color="#e8a0a0", alpha=0.25,
               label=f"t* 95% CI ({ci[0]:.2f}, {ci[1]:.2f})")
    ax.plot(df["threshold"], df["f1"], lw=2.2, color=GT_COLOR[primary],
            label=f"F1 ({GT_LABEL[primary]})")
    ax.plot(df["threshold"], df["precision"], ls="--", lw=1.4,
            color="#2e7d32", label="Precision")
    ax.plot(df["threshold"], df["recall"], ls=":", lw=1.6,
            color="#e08214", label="Recall")
    ax.axvline(t_star, color="#c62828", ls="--", lw=1.5, label=f"t* = {t_star:.2f}")
    ax.axvline(BASELINE_T, color="gray", ls="--", lw=1.3,
               label=f"비교 기준 {BASELINE_T:.2f}")
    ax.set_title(f"임계값 스윕 — Precision / Recall / F1 (부트스트랩 {n_boot:,}회)")
    ax.set_xlabel("임계값 t")
    ax.set_ylabel("모집단 가중 지표")
    ax.set_xlim(float(df["threshold"].min()), float(df["threshold"].max()))
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _mark(ax, df, t, color):
    """PR 곡선 위의 특정 임계값 지점에 점과 라벨을 찍는다."""
    row = df.iloc[(df["threshold"] - t).abs().argmin()]
    ax.plot(row["recall"], row["precision"], "o", color=color, ms=8, zorder=5)
    ax.annotate(f"t={t:.2f}\nP={row['precision']:.2f} R={row['recall']:.2f}",
                (row["recall"], row["precision"]),
                textcoords="offset points", xytext=(10, 6),
                color=color, fontsize=9)


def plot_pr_curve(curves, primary, path):
    """정답지별 PR 곡선 + 주 정답지의 t*·비교 기준 지점 표시."""
    use_korean_font()
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for gt, c in curves.items():
        df = c["sweep"]
        ax.plot(df["recall"], df["precision"], lw=1.8, color=GT_COLOR[gt],
                label=f"{GT_LABEL[gt]} (PR-AUC {pr_auc(df):.3f})")
    df = curves[primary]["sweep"]
    _mark(ax, df, BASELINE_T, "gray")
    _mark(ax, df, curves[primary]["tstar"], "#c62828")
    ax.set_title(f"PR 곡선 — 임계값 스윕 {THRESH_LO:.2f}~{THRESH_HI:.2f}")
    ax.set_xlabel("Recall (모집단 가중)")
    ax.set_ylabel("Precision (모집단 가중)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="course_all_aggregated.csv")
    ap.add_argument("--out", default="results/rq1")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-bin", type=int, nargs=6, default=PER_BIN)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--no-llm", action="store_true", help="LLM 호출 생략(TF-IDF만)")
    ap.add_argument("--reuse-llm", metavar="DIR",
                    help="기존 llm_labels_pass{1,2}.csv 를 재사용(API 재호출 없이 그림·지표 재현)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    use_korean_font()   # 축·범례의 한글이 깨지지 않도록

    df = load_course_data(args.csv)
    pairs = valid_pair_indices(df)
    sim = compute_hybrid_similarity(df)
    sims = np.array([sim[i][j] for i, j in pairs])

    sample, N_k = stratified_sample(pairs, sims, args.per_bin, seed=args.seed)
    json.dump({"N_k": N_k, "per_bin": args.per_bin, "n_valid_pairs": int(len(pairs))},
              open(f"{args.out}/strata.json", "w"), ensure_ascii=False, indent=2)

    names = df["교과목 이름"].fillna("").tolist()
    descs = df["교과목개요"].fillna("").tolist()
    sheet = pd.DataFrame([{
        "pair_id": sp.pair_id, "과목A_이름": names[sp.i], "과목A_개요": descs[sp.i],
        "과목B_이름": names[sp.j], "과목B_개요": descs[sp.j], "label": "",
    } for sp in sample])
    # sample 은 유사도 구간 순이라 그대로 쓰면 앞쪽에 무관 쌍, 뒤쪽에 고유사 쌍이 몰린다.
    # 사람이 채점할 때 뒷부분을 무비판적으로 인정 처리하는 적응 편향이 생기므로 행을 섞는다.
    # (LLM 트랙은 쌍 단위 독립 호출이라 영향 없음. 레이블은 pair_id 로 조인되므로 순서 무관.)
    sheet = sheet.sample(frac=1, random_state=args.seed).reset_index(drop=True)
    sheet.to_csv(f"{args.out}/labeling_sheet.csv", index=False, encoding="utf-8-sig")

    # 쌍별 (유사도·층·가중치)를 남긴다. 이게 없으면 임계값 재분석마다
    # SBERT 임베딩부터 다시 계산해야 한다. 레이블은 pair_id 로 조인한다.
    pd.DataFrame([{
        "pair_id": sp.pair_id, "i": sp.i, "j": sp.j,
        "sim": sp.sim, "bin_idx": sp.bin_idx, "weight": sp.weight,
    } for sp in sample]).to_csv(f"{args.out}/pairs_labeled.csv", index=False)

    tfidf = tfidf_labels(df, sample)
    pd.DataFrame([{"pair_id": k, "label": v} for k, v in tfidf.items()]).to_csv(
        f"{args.out}/tfidf_labels.csv", index=False)

    results = {"tfidf": tfidf}
    if args.reuse_llm:
        p1, p2 = (_read_labels(f"{args.reuse_llm}/llm_labels_{t}.csv")
                  for t in ("pass1", "pass2"))
        expected = {sp.pair_id for sp in sample}
        for tag, p in (("pass1", p1), ("pass2", p2)):
            if set(p) != expected:
                raise SystemExit(
                    f"{args.reuse_llm}/llm_labels_{tag}.csv 의 pair_id 가 현재 표본과 다릅니다 "
                    f"(레이블 {len(p)}건 vs 표본 {len(expected)}건). "
                    "동일한 --seed·--per-bin·입력 CSV 로 만든 레이블이어야 합니다.")
        gold = _adjudicate(p1, p2)
        _finish_llm(results, sample, p1, p2, gold)
    elif not args.no_llm:
        client = _make_openai_client()
        p1 = label_pairs(df, sample, client, seed=args.seed)
        p2 = label_pairs(df, sample, client, seed=args.seed + 1)
        for tag, p in (("pass1", p1), ("pass2", p2)):
            pd.DataFrame([{"pair_id": k, "label": v} for k, v in p.items()]).to_csv(
                f"{args.out}/llm_labels_{tag}.csv", index=False)
        _finish_llm(results, sample, p1, p2, _adjudicate(p1, p2))

    thresholds = np.arange(THRESH_LO, THRESH_HI + THRESH_STEP / 2, THRESH_STEP)
    ids = [sp.pair_id for sp in sample]
    summary = {"N_k": N_k, "n_valid_pairs": int(len(pairs))}
    if "llm" in results:
        summary["inter_llm_kappa"] = results["_inter_llm_kappa"]
        summary["llm_vs_tfidf_kappa"] = cohen_kappa(
            [results["llm"][i] for i in ids], [tfidf[i] for i in ids])
        summary["gt_confusion"] = confusion_2x2(
            [results["llm"][i] for i in ids], [tfidf[i] for i in ids])

    # 스윕·부트스트랩을 먼저 모두 계산한 뒤 그림을 그린다.
    curves = {}
    for gt in [g for g in ("llm", "tfidf") if g in results]:
        labels = results[gt]
        df_sweep = sweep(sample, labels, thresholds)
        df_sweep.to_csv(f"{args.out}/sweep_metrics_{gt}.csv", index=False)
        boot = bootstrap_curves(sample, labels, thresholds,
                                n_boot=args.n_boot, seed=args.seed)
        t_star = best_threshold(df_sweep)
        ci = [float(np.percentile(boot["tstar"], 2.5)),
              float(np.percentile(boot["tstar"], 97.5))]
        summary[f"tstar_{gt}"] = t_star
        summary[f"pr_auc_{gt}"] = pr_auc(df_sweep)
        summary[f"tstar_{gt}_ci"] = ci
        curves[gt] = {"sweep": df_sweep, "boot": boot, "tstar": t_star, "ci": ci}

    # 주 정답지: LLM 골드가 있으면 그것, 없으면(--no-llm) TF-IDF.
    primary = "llm" if "llm" in curves else "tfidf"
    plot_f1_threshold(curves, primary, args.n_boot, f"{args.out}/f1_threshold.png")
    plot_pr_curve(curves, primary, f"{args.out}/pr_curve.png")

    json.dump(summary, open(f"{args.out}/summary.json", "w"), ensure_ascii=False, indent=2)
    with open(f"{args.out}/summary.md", "w") as f:
        f.write("# RQ1 요약\n\n")
        for k, v in summary.items():
            f.write(f"- **{k}**: {v}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
