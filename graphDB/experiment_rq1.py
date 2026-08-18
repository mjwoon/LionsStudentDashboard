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

# 상위 3구간(≥0.7)은 모집단이 희박(실측 64/34/17)해 전수 레이블링한다.
# 큰 값 → stratified_sample 의 min(per_bin, N_k) 로 자동 전수.
CENSUS = 10**9
PER_BIN = [100, 60, 60, CENSUS, CENSUS, CENSUS]


def _make_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _adjudicate(p1: dict, p2: dict) -> dict:
    # 2회 불일치는 보수적으로 '인정 안 함'(0)으로 확정
    return {pid: (1 if p1[pid] == 1 and p2[pid] == 1 else 0) for pid in p1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="course_all_aggregated.csv")
    ap.add_argument("--out", default="results/rq1")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-bin", type=int, nargs=6, default=PER_BIN)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--no-llm", action="store_true", help="LLM 호출 생략(TF-IDF만)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

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
    sheet.to_csv(f"{args.out}/labeling_sheet.csv", index=False, encoding="utf-8-sig")

    tfidf = tfidf_labels(df, sample)
    pd.DataFrame([{"pair_id": k, "label": v} for k, v in tfidf.items()]).to_csv(
        f"{args.out}/tfidf_labels.csv", index=False)

    results = {"tfidf": tfidf}
    if not args.no_llm:
        client = _make_openai_client()
        p1 = label_pairs(df, sample, client, seed=args.seed)
        p2 = label_pairs(df, sample, client, seed=args.seed + 1)
        for tag, p in (("pass1", p1), ("pass2", p2)):
            pd.DataFrame([{"pair_id": k, "label": v} for k, v in p.items()]).to_csv(
                f"{args.out}/llm_labels_{tag}.csv", index=False)
        gold = _adjudicate(p1, p2)
        ids = [sp.pair_id for sp in sample]
        inter_llm_k = cohen_kappa([p1[i] for i in ids], [p2[i] for i in ids])
        results["llm"] = gold
        results["_inter_llm_kappa"] = inter_llm_k

    thresholds = np.arange(0.30, 1.001, 0.01)
    ids = [sp.pair_id for sp in sample]
    summary = {"N_k": N_k, "n_valid_pairs": int(len(pairs))}
    if "llm" in results:
        summary["inter_llm_kappa"] = results["_inter_llm_kappa"]
        summary["llm_vs_tfidf_kappa"] = cohen_kappa(
            [results["llm"][i] for i in ids], [tfidf[i] for i in ids])
        summary["gt_confusion"] = confusion_2x2(
            [results["llm"][i] for i in ids], [tfidf[i] for i in ids])

    fig, ax = plt.subplots(figsize=(9, 5))
    for gt in [g for g in ("llm", "tfidf") if g in results]:
        labels = results[gt]
        df_sweep = sweep(sample, labels, thresholds)
        df_sweep.to_csv(f"{args.out}/sweep_metrics_{gt}.csv", index=False)
        boot = bootstrap_curves(sample, labels, thresholds, n_boot=args.n_boot, seed=args.seed)
        t_star = best_threshold(df_sweep)
        summary[f"tstar_{gt}"] = t_star
        summary[f"pr_auc_{gt}"] = pr_auc(df_sweep)
        summary[f"tstar_{gt}_ci"] = [float(np.percentile(boot["tstar"], 2.5)),
                                     float(np.percentile(boot["tstar"], 97.5))]
        ax.plot(df_sweep["threshold"], df_sweep["f1"], label=f"F1 ({gt}) t*={t_star:.2f}")
        ax.fill_between(thresholds, boot["f1_lo"], boot["f1_hi"], alpha=0.15)
    ax.axvline(0.70, color="gray", ls="--", alpha=0.6, label="현행 0.70")
    ax.axvline(0.80, color="red", ls="--", alpha=0.6, label="실효 0.80")
    ax.set_xlabel("threshold")
    ax.set_ylabel("F1")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{args.out}/f1_threshold.png", dpi=150)
    plt.close(fig)

    json.dump(summary, open(f"{args.out}/summary.json", "w"), ensure_ascii=False, indent=2)
    with open(f"{args.out}/summary.md", "w") as f:
        f.write("# RQ1 요약\n\n")
        for k, v in summary.items():
            f.write(f"- **{k}**: {v}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
