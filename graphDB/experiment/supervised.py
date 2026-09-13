r"""지도학습 분류기와 임계값의 공정한 비교.

Kim 등(EDM 2025)은 교과목 동등성 판정에서 **임계값 방식을 명시적으로 배제**하고
임베딩 차이 벡터에 전통적 분류기를 학습시켰다. 유사도의 결정 경계를 찾는 일이
"실현 가능하지 않다"는 것이 그 근거였다.

다만 그 판단은 측정이 아니라 설계 선택이었고, 무엇보다 **전제가 다르다.** 이들은
Assist.org 학점인정 협약이라는 레이블 자원으로 동등·비동등 각 5,660쌍의 균형
데이터를 만들 수 있었다. 본 연구의 환경에는 그런 코퍼스가 없고 레이블은 335쌍,
양성은 59개이며 모집단 양성률은 0.009%다.

그래서 여기서 묻는 것은 "지도학습이 임계값보다 나은가"가 아니라
**"이 레이블 예산에서 지도학습이라는 선택지가 실제로 존재하는가"** 이다.

공정성을 위해 두 가지를 지킨다.

1. **임계값도 학습 폴드에서 고른다.** t* 를 전체 데이터로 정한 뒤 같은 데이터에서
   평가하면 임계값이 시험 데이터를 본 셈이 된다. 분류기와 동일하게 폴드마다
   학습 구간에서 t 를 고르고 시험 구간에 적용한다.
2. **평가는 모집단 가중(HT)으로 한다.** 표본 양성률 17.6% 와 모집단 양성률
   0.009% 가 다르므로, 가중 없는 지표는 이 문제의 난이도를 감춘다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from experiment.folds import band_stratified_folds
from experiment.metrics import prf


def pair_features(emb: np.ndarray, pairs) -> np.ndarray:
    """쌍 (i,j) -> [|u-v|, u*v]. 대체 인정은 대칭 관계이므로 대칭 특징만 쓴다.

    (Kim 등의 '차이 벡터'에 원소곱을 더한 형태. u,v 를 그대로 넣으면 순서에
    의존해 같은 쌍이 두 값을 갖는다.)
    """
    idx = np.asarray(list(pairs), dtype=int)
    u, v = emb[idx[:, 0]], emb[idx[:, 1]]
    return np.hstack([np.abs(u - v), u * v])


def default_model():
    """고차원·소표본이므로 강한 정규화 + 클래스 불균형 보정."""
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.05, max_iter=5000, class_weight="balanced"),
    )


def oof_supervised(sample, labels, X, n_folds: int = 5, seed: int = 42,
                   model_factory=default_model):
    """층 내 교차검증 out-of-fold 이진 예측. 반환: (예측 dict, 폴드 dict)."""
    folds = band_stratified_folds(sample, n_folds=n_folds, seed=seed)
    order = {sp.pair_id: k for k, sp in enumerate(sample)}
    y = np.array([labels[sp.pair_id] for sp in sample])
    preds: dict[int, int] = {}
    for f in range(n_folds):
        tr = [sp for sp in sample if folds[sp.pair_id] != f]
        te = [sp for sp in sample if folds[sp.pair_id] == f]
        if not te:
            continue
        tr_i = [order[sp.pair_id] for sp in tr]
        te_i = [order[sp.pair_id] for sp in te]
        if len(set(y[tr_i])) < 2:
            for sp in te:
                preds[sp.pair_id] = int(y[tr_i][0])
            continue
        model = model_factory()
        model.fit(X[tr_i], y[tr_i])
        for sp, p in zip(te, model.predict(X[te_i])):
            preds[sp.pair_id] = int(p)
    return preds, folds


def oof_threshold_baseline(sample, labels, thresholds, n_folds: int = 5, seed: int = 42):
    """임계값 기준선 — 폴드마다 학습 구간에서 가중 F1 최대 t 를 골라 시험 구간에 적용.

    반환: (예측 dict, 폴드별 선택된 t 리스트).
    """
    folds = band_stratified_folds(sample, n_folds=n_folds, seed=seed)
    preds: dict[int, int] = {}
    chosen: list[float] = []
    for f in range(n_folds):
        tr = [sp for sp in sample if folds[sp.pair_id] != f]
        te = [sp for sp in sample if folds[sp.pair_id] == f]
        if not te:
            continue
        best_t, best_f1 = float(thresholds[0]), -1.0
        for t in thresholds:
            tp = fp = fn = 0.0
            for sp in tr:
                yy, pred = labels[sp.pair_id], sp.sim >= float(t)
                if pred and yy == 1:
                    tp += sp.weight
                elif pred and yy == 0:
                    fp += sp.weight
                elif not pred and yy == 1:
                    fn += sp.weight
            _, _, f1 = prf(tp, fp, fn)
            if f1 > best_f1:
                best_t, best_f1 = float(t), f1
        chosen.append(best_t)
        for sp in te:
            preds[sp.pair_id] = int(sp.sim >= best_t)
    return preds, chosen


def weighted_prf_from_preds(sample, labels, preds):
    """이진 예측 dict 로부터 모집단 가중 P/R/F1."""
    tp = fp = fn = 0.0
    for sp in sample:
        if sp.pair_id not in preds:
            continue
        yy, pred = labels[sp.pair_id], preds[sp.pair_id]
        if pred and yy == 1:
            tp += sp.weight
        elif pred and yy == 0:
            fp += sp.weight
        elif not pred and yy == 1:
            fn += sp.weight
    return prf(tp, fp, fn)


def feature_sets(emb: np.ndarray, pairs, sims) -> dict:
    """비교할 특징 구성. 차이 벡터 단독이 Kim 등이 실제로 쓴 형태다."""
    full = pair_features(emb, pairs)
    half = full.shape[1] // 2
    return {
        "diff": full[:, :half],
        "diff+prod": full,
        "diff+prod+sim": np.hstack([full, np.asarray(sims).reshape(-1, 1)]),
    }


def model_zoo() -> dict:
    """분류기 후보 격자.

    한 설정만 써서 지면 "기준선을 일부러 약하게 잡았다"는 반론을 받는다.
    지도학습 쪽에 최대한 유리한 설정을 찾기 위해 격자를 훑는다.
    """
    def lr(c):
        return lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(C=c, max_iter=5000, class_weight="balanced"))

    def svc(c):
        return lambda: make_pipeline(
            StandardScaler(),
            LinearSVC(C=c, class_weight="balanced", max_iter=20000))

    def rf():
        return RandomForestClassifier(n_estimators=400, class_weight="balanced",
                                      random_state=0, min_samples_leaf=2)

    zoo = {"LR C=%g" % c: lr(c) for c in (0.01, 0.05, 0.2, 1.0)}
    zoo.update({"LinearSVC C=%g" % c: svc(c) for c in (0.01, 0.1)})
    zoo["RandomForest"] = rf
    return zoo


def sweep_supervised(sample, labels, emb, n_folds: int = 5, seed: int = 42):
    """특징 x 모델 격자를 모두 out-of-fold 로 평가. F1 내림차순 DataFrame."""
    pairs = [(sp.i, sp.j) for sp in sample]
    sims = [sp.sim for sp in sample]
    rows = []
    for fname, X in feature_sets(emb, pairs, sims).items():
        for mname, factory in model_zoo().items():
            preds, _ = oof_supervised(sample, labels, X, n_folds=n_folds,
                                      seed=seed, model_factory=factory)
            p, r, f = weighted_prf_from_preds(sample, labels, preds)
            rows.append({"features": fname, "model": mname,
                         "n_features": int(X.shape[1]),
                         "precision": p, "recall": r, "f1": f})
    return pd.DataFrame(rows).sort_values("f1", ascending=False).reset_index(drop=True)
