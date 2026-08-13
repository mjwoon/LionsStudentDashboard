# 교과목 유사도 임계값 실험 (RQ1·RQ2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대체 인정 유사도 임계값의 최적값 `t*`를 실험적으로 산출(RQ1)하고, 임계값 변화가 12,000건(고유 학생 300 × 평가대상 학과 40) 평가의 점수·학과 순위에 미치는 영향을 측정(RQ2)하는 재현 가능한 실험 하니스를 만든다.

**Architecture:** 순수 계산 유닛(표본추출·가중 지표·부트스트랩·κ·유사도 lookup·영향 지표)은 TDD로 개별 구현하고, LLM 레이블링·플롯·오케스트레이션은 그 위에서 조립한다. RQ1은 하이브리드 유사도(0.7·SBERT + 0.3·TF-IDF) 위에서 층화표본 400쌍을 LLM 골드·TF-IDF silver 두 GT로 채점해 가중 P/R/F1을 스윕한다. RQ2는 SQLite에 CSV를 시딩하고 `EvaluationService`에 유사도·가변 임계값을 주입(Neo4j 우회)해 임계값별 전면 재계산한다.

**Tech Stack:** Python, numpy, pandas, scikit-learn, sentence-transformers, matplotlib, OpenAI SDK, SQLAlchemy, FastAPI TestClient, pytest.

## Global Constraints

- 유사도 정의: 프로덕션 하이브리드 `0.7·SBERT + 0.3·TF-IDF` (SBERT = `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`). 순수 SBERT 아님.
- 유효 쌍: 같은 학수번호 쌍·연계과목(1,2 시리즈) 쌍 제외 (`graphDB/text_features.is_sequential_course` 사용).
- 재현성: 모든 무작위 과정(표본추출·부트스트랩·LLM 순서 섞기)에 시드 고정. 기본 시드 `42`.
- LLM 레이블러: OpenAI `gpt-4o`, `.env`의 `OPENAI_API_KEY` 사용. 2회 독립 실행.
- 데이터: `graphDB/course_all_aggregated.csv`(854과목), `sample_students_300.csv`, `sample_enrollments_300.csv`, `group1_colleges_depts_.csv`, `group3_courses.csv`, `group4_교육과정_전체.csv`, `group5_requirements_recs.csv`.
- 산출 위치: `graphDB/results/rq1/`, `graphDB/results/rq2/`.
- 임계값 스윕: t = 0.30 ~ 1.00, 0.01 단위. RQ2 재계산 임계값: {0.6, 0.7, 0.8, t*}.
- 층화표본: 6구간 [0–0.5:100, 0.5–0.6:60, 0.6–0.7:60, 0.7–0.8:60, 0.8–0.9:60, 0.9–1.0:60], 층별 모집단 `N_k` 기록.
- 테스트: `pytest`. 실험 유닛 테스트는 `graphDB/tests/experiment/`.
- 커밋: 태스크마다 빈번히. 실제 OpenAI 호출·SBERT 다운로드가 필요한 테스트는 유닛 테스트에서 제외(모킹/주입).

---

## File Structure

```
graphDB/experiment/
  __init__.py
  sampling.py          # 층화표본 추출 + N_k
  metrics.py           # 가중(HT) P/R/F1 스윕, PR-AUC, t*
  bootstrap.py         # 층 내 재표집 부트스트랩 CI
  kappa.py             # Cohen's κ
  tfidf_labeler.py     # TF-IDF silver 레이블
  llm_labeler.py       # OpenAI gpt-4o 이진 레이블러 (client 주입)
  similarity_lookup.py # code→code 하이브리드 유사도 dict
  seeding.py           # CSV → SQLite (FastAPI TestClient 재사용)
  injected_eval.py     # EvaluationService 주입 서브클래스
  impact_metrics.py    # Spearman ρ, Top-1 변경률, 등급 이동, 점수 분포
graphDB/experiment_rq1.py   # RQ1 오케스트레이터 (CLI)
graphDB/experiment_rq2.py   # RQ2 오케스트레이터 (CLI)
graphDB/tests/experiment/
  test_sampling.py
  test_metrics.py
  test_bootstrap.py
  test_kappa.py
  test_tfidf_labeler.py
  test_llm_labeler.py
  test_similarity_lookup.py
  test_injected_eval.py
  test_impact_metrics.py
graphDB/tests/experiment/test_seeding_integration.py  # 실 CSV 시딩 스모크
```

**공용 데이터 계약**: 유사도가 매겨진 쌍은 `SampledPair`(dataclass)로 오간다:
`pair_id:int, i:int, j:int, sim:float, bin_idx:int, weight:float`.
레이블은 `pair_id → int(0/1)` dict.

---

## Task 1: 실험 패키지 스캐폴드 + 유사도 원천 함수

**Files:**
- Create: `graphDB/experiment/__init__.py`
- Create: `graphDB/experiment/pairs.py`
- Test: `graphDB/tests/experiment/test_pairs.py`

**Interfaces:**
- Produces:
  - `@dataclass SampledPair(pair_id:int, i:int, j:int, sim:float, bin_idx:int, weight:float)`
  - `compute_hybrid_similarity(df: pd.DataFrame, engine: SimilarityEngine|None=None) -> np.ndarray` — n×n 하이브리드 유사도 행렬. `engine=None`이면 실제 SBERT 로드.
  - `valid_pair_indices(df: pd.DataFrame) -> np.ndarray` — shape (P,2), 유효 상삼각 쌍 (i,j).

**Consumes:** `graphDB/similarity_engine.py`(`SimilarityEngine`, `load_course_data`), `graphDB/text_features.py`(`is_sequential_course`).

- [ ] **Step 1: 실패 테스트 작성** — `test_pairs.py`

```python
import numpy as np
import pandas as pd
from experiment.pairs import valid_pair_indices, compute_hybrid_similarity, SampledPair


def _df():
    # 학수번호 중복(A) 1쌍과 연계과목(미적분학1/미적분학2) 1쌍이 제외되어야 한다
    return pd.DataFrame({
        "교과목 이름": ["미적분학1", "미적분학2", "물리학", "화학"],
        "교과목개요": ["극한", "적분", "역학", "반응"],
        "학수번호": ["X1", "X2", "SAME", "SAME"],
    })


def test_valid_pairs_excludes_same_code_and_sequential():
    pairs = valid_pair_indices(_df())
    got = {tuple(p) for p in pairs}
    # (0,1)=연계 제외, (2,3)=같은 학수번호 제외. 나머지 4쌍만 유효.
    assert (0, 1) not in got and (2, 3) not in got
    assert len(got) == 4


def test_hybrid_similarity_is_symmetric_with_injected_model():
    df = _df()
    # 주입 모델: 고정 임베딩 → SBERT 다운로드 없이 테스트
    class FakeModel:
        def encode(self, texts, **kw):
            rng = np.random.default_rng(0)
            return rng.random((len(texts), 8))
    from similarity_engine import SimilarityEngine
    eng = SimilarityEngine(model=FakeModel())
    sim = compute_hybrid_similarity(df, engine=eng)
    assert sim.shape == (4, 4)
    assert np.allclose(sim, sim.T, atol=1e-6)
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_pairs.py -v` → FAIL (module not found)

- [ ] **Step 3: 구현** — `graphDB/experiment/__init__.py`는 빈 파일. `graphDB/experiment/pairs.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from text_features import is_sequential_course


@dataclass
class SampledPair:
    pair_id: int
    i: int
    j: int
    sim: float
    bin_idx: int
    weight: float


def valid_pair_indices(df: pd.DataFrame) -> np.ndarray:
    codes = df["학수번호"].fillna("").astype(str).tolist() if "학수번호" in df else [""] * len(df)
    names = df["교과목 이름"].tolist()
    n = len(df)
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            if codes[i] and codes[i] == codes[j]:
                continue
            if is_sequential_course(names[i], names[j]):
                continue
            out.append((i, j))
    return np.array(out, dtype=int) if out else np.empty((0, 2), dtype=int)


def compute_hybrid_similarity(df, engine=None) -> np.ndarray:
    from similarity_engine import SimilarityEngine
    if engine is None:
        engine = SimilarityEngine()
    if "feature_text" not in df:
        df = df.copy()
        df["feature_text"] = df["교과목 이름"] + " " + df["교과목개요"].fillna("")
    emb = engine.create_embeddings(df, use_tfidf_weighting=True)
    return engine._similarity_matrix(emb)
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_pairs.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/__init__.py graphDB/experiment/pairs.py graphDB/tests/experiment/test_pairs.py
git commit -m "feat(experiment): valid pairs + hybrid similarity source"
```

---

## Task 2: 층화표본 추출

**Files:**
- Create: `graphDB/experiment/sampling.py`
- Test: `graphDB/tests/experiment/test_sampling.py`

**Interfaces:**
- Consumes: `SampledPair` (Task 1).
- Produces:
  - `BINS = [(0.0,0.5),(0.5,0.6),(0.6,0.7),(0.7,0.8),(0.8,0.9),(0.9,1.0001)]`
  - `bin_index(sim: float) -> int` — 구간 인덱스(0..5), 범위 밖이면 -1.
  - `stratified_sample(pairs: np.ndarray, sims: np.ndarray, per_bin: list[int], seed: int=42) -> tuple[list[SampledPair], list[int]]` — 반환: (샘플 리스트, `N_k` 층별 모집단 크기). `weight = N_k / min(per_bin_k, N_k)`.

- [ ] **Step 1: 실패 테스트 작성** — `test_sampling.py`

```python
import numpy as np
from experiment.sampling import bin_index, stratified_sample, BINS


def test_bin_index_boundaries():
    assert bin_index(0.0) == 0
    assert bin_index(0.49) == 0
    assert bin_index(0.5) == 1
    assert bin_index(0.75) == 3
    assert bin_index(1.0) == 5


def test_stratified_sample_counts_and_weights_and_determinism():
    rng = np.random.default_rng(0)
    # 각 구간에 정확히 200개씩 모집단 배치
    sims = np.concatenate([np.full(200, c + 0.01) for c in
                           (0.0, 0.5, 0.6, 0.7, 0.8, 0.9)])
    pairs = np.stack([np.arange(len(sims)), np.arange(len(sims)) + 1], axis=1)
    per_bin = [100, 60, 60, 60, 60, 60]
    sample, N_k = stratified_sample(pairs, sims, per_bin, seed=42)
    assert N_k == [200, 200, 200, 200, 200, 200]
    counts = [sum(1 for s in sample if s.bin_idx == b) for b in range(6)]
    assert counts == per_bin
    # weight = N_k / n_k
    w0 = next(s.weight for s in sample if s.bin_idx == 0)
    assert abs(w0 - 200 / 100) < 1e-9
    # 결정성: 같은 시드 → 같은 pair_id 집합
    sample2, _ = stratified_sample(pairs, sims, per_bin, seed=42)
    assert [s.i for s in sample] == [s.i for s in sample2]
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_sampling.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/sampling.py`:

```python
from __future__ import annotations
import numpy as np
from experiment.pairs import SampledPair

BINS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]


def bin_index(sim: float) -> int:
    for k, (lo, hi) in enumerate(BINS):
        if lo <= sim < hi:
            return k
    return -1


def stratified_sample(pairs, sims, per_bin, seed: int = 42):
    rng = np.random.default_rng(seed)
    bins = np.array([bin_index(s) for s in sims])
    sample: list[SampledPair] = []
    N_k: list[int] = []
    pid = 0
    for k in range(len(BINS)):
        idx = np.nonzero(bins == k)[0]
        N = len(idx)
        N_k.append(N)
        take = min(per_bin[k], N)
        chosen = rng.choice(idx, size=take, replace=False) if take else np.array([], int)
        weight = (N / take) if take else 0.0
        for c in sorted(chosen.tolist()):
            i, j = int(pairs[c][0]), int(pairs[c][1])
            sample.append(SampledPair(pid, i, j, float(sims[c]), k, weight))
            pid += 1
    return sample, N_k
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_sampling.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/sampling.py graphDB/tests/experiment/test_sampling.py
git commit -m "feat(experiment): stratified sampling with population weights"
```

---

## Task 3: 가중(Horvitz-Thompson) P/R/F1 스윕 + PR-AUC + t*

**Files:**
- Create: `graphDB/experiment/metrics.py`
- Test: `graphDB/tests/experiment/test_metrics.py`

**Interfaces:**
- Consumes: `SampledPair` (Task 1).
- Produces:
  - `weighted_confusion(sample, labels: dict[int,int], t: float) -> tuple[float,float,float]` — 가중 (TP,FP,FN). 각 쌍 기여 `weight`.
  - `prf(tp,fp,fn) -> tuple[float,float,float]` — (precision, recall, f1), 분모 0이면 0.0.
  - `sweep(sample, labels, thresholds: np.ndarray) -> pd.DataFrame` — 열: threshold, precision, recall, f1.
  - `pr_auc(df) -> float` — recall 정렬 후 사다리꼴 적분.
  - `best_threshold(df) -> float` — f1 최대의 threshold (동률이면 최소 t).

설계서의 bin 단위 추정식은 t가 구간 경계일 때 본 HT 추정의 특수형이다(각 쌍에 `weight=N_k/n_k` 부여 → `Σ_{sim≥t} weight·label` = `Σ_{구간≥t} N_k·p_k`).

- [ ] **Step 1: 실패 테스트 작성** — `test_metrics.py`

```python
import numpy as np
from experiment.pairs import SampledPair
from experiment.metrics import weighted_confusion, prf, sweep, best_threshold, pr_auc


def _sample():
    # 두 층: 층0 weight=2, 층1 weight=5
    return [
        SampledPair(0, 0, 1, 0.40, 0, 2.0),  # label 0
        SampledPair(1, 0, 2, 0.72, 0, 2.0),  # label 1
        SampledPair(2, 0, 3, 0.85, 1, 5.0),  # label 1
        SampledPair(3, 0, 4, 0.90, 1, 5.0),  # label 0
    ]


def test_weighted_confusion_matches_bin_formula():
    labels = {0: 0, 1: 1, 2: 1, 3: 0}
    tp, fp, fn = weighted_confusion(_sample(), labels, t=0.70)
    # sim>=0.70: pairs 1,2,3. TP=1*2 + 1*5 =7 ; FP=3->0*5=5 ; FN=0
    assert (tp, fp, fn) == (7.0, 5.0, 0.0)


def test_prf_zero_safe():
    assert prf(0, 0, 0) == (0.0, 0.0, 0.0)


def test_sweep_and_best_threshold():
    labels = {0: 0, 1: 1, 2: 1, 3: 0}
    df = sweep(_sample(), labels, np.arange(0.30, 1.001, 0.01))
    assert set(df.columns) >= {"threshold", "precision", "recall", "f1"}
    t = best_threshold(df)
    assert 0.30 <= t <= 1.0
    assert 0.0 <= pr_auc(df) <= 1.0
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_metrics.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/metrics.py`:

```python
from __future__ import annotations
import numpy as np
import pandas as pd


def weighted_confusion(sample, labels, t):
    tp = fp = fn = 0.0
    for sp in sample:
        y = labels[sp.pair_id]
        pred = sp.sim >= t
        if pred and y == 1:
            tp += sp.weight
        elif pred and y == 0:
            fp += sp.weight
        elif (not pred) and y == 1:
            fn += sp.weight
    return tp, fp, fn


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f


def sweep(sample, labels, thresholds):
    rows = []
    for t in thresholds:
        p, r, f = prf(*weighted_confusion(sample, labels, float(t)))
        rows.append({"threshold": round(float(t), 2), "precision": p, "recall": r, "f1": f})
    return pd.DataFrame(rows)


def best_threshold(df) -> float:
    m = df["f1"].max()
    return float(df.loc[df["f1"] >= m - 1e-12, "threshold"].min())


def pr_auc(df) -> float:
    d = df.sort_values("recall")
    return float(np.trapz(d["precision"].values, d["recall"].values))
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_metrics.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/metrics.py graphDB/tests/experiment/test_metrics.py
git commit -m "feat(experiment): weighted PRF sweep, PR-AUC, t*"
```

---

## Task 4: 부트스트랩 신뢰구간 (층 내 재표집)

**Files:**
- Create: `graphDB/experiment/bootstrap.py`
- Test: `graphDB/tests/experiment/test_bootstrap.py`

**Interfaces:**
- Consumes: `sweep`, `best_threshold` (Task 3), `SampledPair`.
- Produces:
  - `bootstrap_curves(sample, labels, thresholds, n_boot:int=1000, seed:int=42) -> dict` — 반환 `{"f1_lo":np.ndarray, "f1_hi":np.ndarray, "precision_lo/hi", "recall_lo/hi", "tstar":np.ndarray}`. 층별 인덱스를 층 내에서 복원추출해 곡선을 재계산, 2.5/97.5 백분위.

- [ ] **Step 1: 실패 테스트 작성** — `test_bootstrap.py`

```python
import numpy as np
from experiment.pairs import SampledPair
from experiment.bootstrap import bootstrap_curves


def _sample():
    return [SampledPair(i, 0, i + 1, 0.5 + 0.05 * i, i % 2, 2.0) for i in range(10)]


def test_bootstrap_shapes_and_bounds():
    labels = {i: (1 if i % 2 else 0) for i in range(10)}
    th = np.arange(0.30, 1.001, 0.01)
    out = bootstrap_curves(_sample(), labels, th, n_boot=50, seed=42)
    assert out["f1_lo"].shape == th.shape
    assert np.all(out["f1_lo"] <= out["f1_hi"] + 1e-9)
    assert out["tstar"].shape == (50,)
    # 결정성
    out2 = bootstrap_curves(_sample(), labels, th, n_boot=50, seed=42)
    assert np.allclose(out["f1_lo"], out2["f1_lo"])
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_bootstrap.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/bootstrap.py`:

```python
from __future__ import annotations
import numpy as np
from collections import defaultdict
from experiment.metrics import sweep, best_threshold


def bootstrap_curves(sample, labels, thresholds, n_boot: int = 1000, seed: int = 42):
    rng = np.random.default_rng(seed)
    by_bin = defaultdict(list)
    for sp in sample:
        by_bin[sp.bin_idx].append(sp)
    keys = ("precision", "recall", "f1")
    stacks = {k: [] for k in keys}
    tstars = []
    for _ in range(n_boot):
        resampled = []
        for _, members in by_bin.items():
            idx = rng.integers(0, len(members), size=len(members))
            resampled.extend(members[t] for t in idx)
        df = sweep(resampled, labels, thresholds)
        for k in keys:
            stacks[k].append(df[k].values)
        tstars.append(best_threshold(df))
    out = {}
    for k in keys:
        arr = np.vstack(stacks[k])
        out[f"{k}_lo"] = np.percentile(arr, 2.5, axis=0)
        out[f"{k}_hi"] = np.percentile(arr, 97.5, axis=0)
    out["tstar"] = np.array(tstars, dtype=float)
    return out
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_bootstrap.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/bootstrap.py graphDB/tests/experiment/test_bootstrap.py
git commit -m "feat(experiment): stratified bootstrap CI for PRF curves"
```

---

## Task 5: Cohen's κ

**Files:**
- Create: `graphDB/experiment/kappa.py`
- Test: `graphDB/tests/experiment/test_kappa.py`

**Interfaces:**
- Produces: `cohen_kappa(a: list[int], b: list[int]) -> float`, `confusion_2x2(a,b) -> dict` (`{"n11","n10","n01","n00"}`).

- [ ] **Step 1: 실패 테스트 작성** — `test_kappa.py`

```python
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
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_kappa.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/kappa.py`:

```python
from __future__ import annotations


def confusion_2x2(a, b):
    n11 = sum(1 for x, y in zip(a, b) if x == 1 and y == 1)
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n00 = sum(1 for x, y in zip(a, b) if x == 0 and y == 0)
    return {"n11": n11, "n10": n10, "n01": n01, "n00": n00}


def cohen_kappa(a, b) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_kappa.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/kappa.py graphDB/tests/experiment/test_kappa.py
git commit -m "feat(experiment): cohen kappa + 2x2 confusion"
```

---

## Task 6: TF-IDF silver 레이블러

**Files:**
- Create: `graphDB/experiment/tfidf_labeler.py`
- Test: `graphDB/tests/experiment/test_tfidf_labeler.py`

**Interfaces:**
- Consumes: `SampledPair`, `graphDB/text_features.build_name_char_tfidf`.
- Produces: `tfidf_labels(df, sample, threshold: float=0.30) -> dict[int,int]` — 이름 char n-gram TF-IDF cosine ≥ threshold이면 1.

- [ ] **Step 1: 실패 테스트 작성** — `test_tfidf_labeler.py`

```python
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
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_tfidf_labeler.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/tfidf_labeler.py`:

```python
from __future__ import annotations
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from text_features import build_name_char_tfidf


def tfidf_labels(df, sample, threshold: float = 0.30):
    names = df["교과목 이름"].fillna("").tolist()
    vec = build_name_char_tfidf()
    mat = vec.fit_transform(names).toarray()
    mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)
    sim = cosine_similarity(mat)
    return {sp.pair_id: int(sim[sp.i][sp.j] >= threshold) for sp in sample}
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_tfidf_labeler.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/tfidf_labeler.py graphDB/tests/experiment/test_tfidf_labeler.py
git commit -m "feat(experiment): tfidf silver labeler"
```

---

## Task 7: LLM 레이블러 (OpenAI gpt-4o, client 주입)

**Files:**
- Create: `graphDB/experiment/llm_labeler.py`
- Test: `graphDB/tests/experiment/test_llm_labeler.py`

**Interfaces:**
- Consumes: `SampledPair`.
- Produces:
  - `build_prompt(a_name,a_desc,b_name,b_desc) -> str`
  - `parse_decision(text: str) -> int` — 응답에서 1/0 추출 (예 → 1, 아니오/불가 → 0, 불명 → 0).
  - `label_pairs(df, sample, client, model="gpt-4o", seed:int=42) -> dict[int,int]` — 각 쌍을 무작위 순서로 제시(A/B 스왑 포함), `client.chat.completions.create` 호출. `client`는 주입(테스트는 fake).

- [ ] **Step 1: 실패 테스트 작성** — `test_llm_labeler.py`

```python
import pandas as pd
from experiment.pairs import SampledPair
from experiment.llm_labeler import parse_decision, label_pairs


def test_parse_decision():
    assert parse_decision("네, 인정 가능합니다") == 1
    assert parse_decision("아니오") == 0
    assert parse_decision("1") == 1
    assert parse_decision("불가능") == 0


class FakeClient:
    """항상 '예'를 반환하는 OpenAI 호환 fake."""
    class chat:
        class completions:
            @staticmethod
            def create(**kw):
                class M: content = "예"
                class C: message = M()
                class R: choices = [C()]
                return R()


def test_label_pairs_uses_client_and_covers_all():
    df = pd.DataFrame({"교과목 이름": ["A", "B"], "교과목개요": ["x", "y"]})
    sample = [SampledPair(0, 0, 1, 0.8, 4, 1.0)]
    labels = label_pairs(df, sample, client=FakeClient(), model="gpt-4o", seed=1)
    assert labels == {0: 1}
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_llm_labeler.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/llm_labeler.py`:

```python
from __future__ import annotations
import re
import numpy as np


def build_prompt(a_name, a_desc, b_name, b_desc) -> str:
    return (
        "너는 대학 학사 담당자다. 학생이 아래 '이수 과목'을 들었을 때, "
        "'대상 과목'을 대체 인정(같은 과목으로 인정)할 수 있는지 판단하라.\n"
        "과목명과 개요만 근거로 삼고, 오직 '예' 또는 '아니오' 한 단어로만 답하라.\n\n"
        f"[이수 과목] 이름: {a_name}\n개요: {a_desc}\n\n"
        f"[대상 과목] 이름: {b_name}\n개요: {b_desc}\n\n답:"
    )


def parse_decision(text: str) -> int:
    t = (text or "").strip().lower()
    if re.search(r"(예|네|가능|인정|yes|^1\b|^1$)", t) and not re.search(r"(아니|불가|불인정|no)", t):
        return 1
    return 0


def label_pairs(df, sample, client, model: str = "gpt-4o", seed: int = 42):
    rng = np.random.default_rng(seed)
    names = df["교과목 이름"].fillna("").tolist()
    descs = df["교과목개요"].fillna("").tolist()
    labels = {}
    for sp in sample:
        i, j = (sp.i, sp.j)
        if rng.random() < 0.5:  # 제시 순서 무작위화 (앵커링 차단)
            i, j = j, i
        prompt = build_prompt(names[i], descs[i], names[j], descs[j])
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        labels[sp.pair_id] = parse_decision(resp.choices[0].message.content)
    return labels
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_llm_labeler.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/llm_labeler.py graphDB/tests/experiment/test_llm_labeler.py
git commit -m "feat(experiment): openai gpt-4o binary labeler (injected client)"
```

---

## Task 8: RQ1 오케스트레이터 (CLI, end-to-end 산출)

**Files:**
- Create: `graphDB/experiment_rq1.py`
- Test: 수동 검증 (실 SBERT·OpenAI 필요 → 유닛 테스트 아님)

**Interfaces:**
- Consumes: Task 1–7 전체. OpenAI client는 `ai/ai_services/ai_service.py`와 동일하게 `from openai import OpenAI; OpenAI(api_key=os.getenv("OPENAI_API_KEY"))`로 생성.
- Produces: `graphDB/results/rq1/` 산출물 일체.

- [ ] **Step 1: 오케스트레이터 작성** — `graphDB/experiment_rq1.py`:

```python
"""RQ1: 대체 인정 최적 임계값 실험 (하이브리드 유사도 + LLM/TF-IDF GT)."""
from __future__ import annotations
import argparse, json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from similarity_engine import load_course_data
from experiment.pairs import valid_pair_indices, compute_hybrid_similarity
from experiment.sampling import stratified_sample
from experiment.tfidf_labeler import tfidf_labels
from experiment.llm_labeler import label_pairs
from experiment.kappa import cohen_kappa, confusion_2x2
from experiment.metrics import sweep, best_threshold, pr_auc
from experiment.bootstrap import bootstrap_curves

PER_BIN = [100, 60, 60, 60, 60, 60]


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
    ax.set_xlabel("threshold"); ax.set_ylabel("F1"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{args.out}/f1_threshold.png", dpi=150); plt.close(fig)

    json.dump(summary, open(f"{args.out}/summary.json", "w"), ensure_ascii=False, indent=2)
    with open(f"{args.out}/summary.md", "w") as f:
        f.write("# RQ1 요약\n\n")
        for k, v in summary.items():
            f.write(f"- **{k}**: {v}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: TF-IDF만으로 스모크 실행** (LLM 비용 없이 파이프라인 검증)

Run: `cd graphDB && python experiment_rq1.py --no-llm --per-bin 20 12 12 12 12 12 --n-boot 50`
Expected: `results/rq1/`에 `strata.json`, `labeling_sheet.csv`, `tfidf_labels.csv`, `sweep_metrics_tfidf.csv`, `f1_threshold.png`, `summary.json/md` 생성. `summary`에 `tstar_tfidf`·`pr_auc_tfidf` 존재. 에러 없이 종료.

- [ ] **Step 3: 산출물 확인** — Run: `cd graphDB && cat results/rq1/summary.md && ls results/rq1`. 값이 채워졌는지 육안 확인.

- [ ] **Step 4: 커밋**

```bash
git add graphDB/experiment_rq1.py graphDB/results/rq1/
git commit -m "feat(experiment): RQ1 orchestrator + tfidf smoke artifacts"
```

- [ ] **Step 5: (선택) LLM 포함 전체 실행** — 사용자 승인 하에 실 OpenAI 호출:

Run: `cd graphDB && python experiment_rq1.py --n-boot 1000`
Expected: `llm_labels_pass1/2.csv`, `sweep_metrics_llm.csv` 추가. `summary`에 `inter_llm_kappa`, `llm_vs_tfidf_kappa`, `tstar_llm`. **RQ2에 넘길 `tstar_llm` 값을 기록**.

---

## Task 9: 유사도 lookup (code→code)

**Files:**
- Create: `graphDB/experiment/similarity_lookup.py`
- Test: `graphDB/tests/experiment/test_similarity_lookup.py`

**Interfaces:**
- Consumes: `compute_hybrid_similarity` (Task 1).
- Produces:
  - `build_lookup(df, sim: np.ndarray, min_keep: float=0.6) -> dict[tuple[str,str], float]` — 학수번호 있는 쌍만, `sim ≥ min_keep`, 키 정렬 `(min(code),max(code))`.
  - `make_similarity_fn(lookup) -> Callable[[str,str], float]` — 대칭 조회, 없으면 0.0.

- [ ] **Step 1: 실패 테스트 작성** — `test_similarity_lookup.py`

```python
import numpy as np
import pandas as pd
from experiment.similarity_lookup import build_lookup, make_similarity_fn


def test_lookup_filters_and_is_symmetric():
    df = pd.DataFrame({"교과목 이름": ["a", "b", "c"], "교과목개요": ["", "", ""],
                       "학수번호": ["C1", "C2", "C3"]})
    sim = np.array([[1.0, 0.9, 0.4], [0.9, 1.0, 0.65], [0.4, 0.65, 1.0]])
    lut = build_lookup(df, sim, min_keep=0.6)
    assert ("C1", "C2") in lut and ("C2", "C3") in lut
    assert ("C1", "C3") not in lut  # 0.4 < 0.6 제외
    fn = make_similarity_fn(lut)
    assert fn("C2", "C1") == 0.9 and fn("C1", "C3") == 0.0
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_similarity_lookup.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/similarity_lookup.py`:

```python
from __future__ import annotations
import numpy as np


def build_lookup(df, sim, min_keep: float = 0.6):
    codes = df["학수번호"].fillna("").astype(str).tolist()
    n = len(codes)
    lut = {}
    iu, ju = np.triu_indices(n, k=1)
    for i, j in zip(iu.tolist(), ju.tolist()):
        ci, cj = codes[i], codes[j]
        if not ci or not cj or ci == cj:
            continue
        s = float(sim[i][j])
        if s >= min_keep:
            lut[(min(ci, cj), max(ci, cj))] = s
    return lut


def make_similarity_fn(lut):
    def fn(a: str, b: str) -> float:
        if a == b:
            return 1.0
        return lut.get((min(a, b), max(a, b)), 0.0)
    return fn
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_similarity_lookup.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/similarity_lookup.py graphDB/tests/experiment/test_similarity_lookup.py
git commit -m "feat(experiment): code-to-code similarity lookup"
```

---

## Task 10: 주입형 EvaluationService

**Files:**
- Create: `graphDB/experiment/injected_eval.py`
- Test: `graphDB/tests/experiment/test_injected_eval.py`

**Interfaces:**
- Consumes: `services.evaluation_service.EvaluationService`, `make_similarity_fn` (Task 9).
- Produces: `InjectedEvaluationService(db, similarity_fn, threshold)` — `_is_graph_available()`는 항상 True, `_get_similarity_from_graph`는 주입 fn 조회, `_similarity_threshold`는 주입값. 다른 로직은 상속 그대로.

- [ ] **Step 1: 실패 테스트 작성** — `test_injected_eval.py` (Task 별 스텁 시딩은 Task 12에서 실 CSV로 검증; 여기선 주입 동작만)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lions_core.models import Base
from experiment.injected_eval import InjectedEvaluationService


def test_injection_overrides_graph_and_threshold():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    calls = {}

    def fake_sim(a, b):
        calls[(a, b)] = True
        return 0.75

    svc = InjectedEvaluationService(db, similarity_fn=fake_sim, threshold=0.72)
    assert svc._is_graph_available() is True
    assert svc._similarity_threshold == 0.72
    assert svc._get_similarity_from_graph("X", "Y") == 0.75
    assert ("X", "Y") in calls
    db.close()
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_injected_eval.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/injected_eval.py`:

```python
from __future__ import annotations
from services.evaluation_service import EvaluationService


class InjectedEvaluationService(EvaluationService):
    """유사도·임계값을 주입하고 Neo4j를 우회한다(오프라인 재현)."""

    def __init__(self, db, similarity_fn, threshold: float):
        super().__init__(db)
        self._similarity_fn = similarity_fn
        self._similarity_threshold = threshold

    def _is_graph_available(self) -> bool:
        return True

    def _get_similarity_from_graph(self, source_course_code, target_course_code) -> float:
        return self._similarity_fn(source_course_code, target_course_code)
```

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_injected_eval.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/injected_eval.py graphDB/tests/experiment/test_injected_eval.py
git commit -m "feat(experiment): injected EvaluationService (bypass neo4j)"
```

---

## Task 11: 영향 지표 (Spearman ρ, Top-1 변경률, 등급 이동)

**Files:**
- Create: `graphDB/experiment/impact_metrics.py`
- Test: `graphDB/tests/experiment/test_impact_metrics.py`

**Interfaces:**
- Produces (입력은 long-format df: 열 `student_id, department_id, overall_score, grade`):
  - `dept_rank_per_student(df) -> dict[student_id, list[(department_id, rank)]]`
  - `spearman_vs_baseline(df, base_df) -> pd.Series` — 학생별 ρ.
  - `top1_change_rate(df, base_df) -> float` — Top-1 학과가 바뀐 학생 비율.
  - `grade_migration(df, base_df) -> pd.DataFrame` — base_grade × new_grade 카운트.

- [ ] **Step 1: 실패 테스트 작성** — `test_impact_metrics.py`

```python
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
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_impact_metrics.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/impact_metrics.py`:

```python
from __future__ import annotations
import pandas as pd
from scipy.stats import spearmanr


def _ranked(df):
    out = {}
    for sid, g in df.groupby("student_id"):
        s = g.sort_values("department_id")
        out[sid] = dict(zip(s["department_id"], s["overall_score"]))
    return out


def top1_change_rate(df, base_df) -> float:
    a, b = _ranked(df), _ranked(base_df)
    changed = total = 0
    for sid in b:
        if sid not in a:
            continue
        total += 1
        top_b = max(b[sid], key=b[sid].get)
        top_a = max(a[sid], key=a[sid].get)
        if top_a != top_b:
            changed += 1
    return changed / total if total else 0.0


def spearman_vs_baseline(df, base_df) -> pd.Series:
    a, b = _ranked(df), _ranked(base_df)
    res = {}
    for sid in b:
        if sid not in a:
            continue
        depts = sorted(set(b[sid]) & set(a[sid]))
        if len(depts) < 2:
            continue
        rho, _ = spearmanr([b[sid][d] for d in depts], [a[sid][d] for d in depts])
        res[sid] = rho
    return pd.Series(res)


def grade_migration(df, base_df) -> pd.DataFrame:
    a = df.set_index(["student_id", "department_id"])["grade"]
    b = base_df.set_index(["student_id", "department_id"])["grade"]
    j = pd.DataFrame({"base": b, "new": a}).dropna()
    return pd.crosstab(j["base"], j["new"])
```

주의: `scipy` 의존 필요. 없으면 `graphDB/pyproject.toml`에 추가하고 `uv sync`.

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_impact_metrics.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/impact_metrics.py graphDB/tests/experiment/test_impact_metrics.py graphDB/pyproject.toml
git commit -m "feat(experiment): impact metrics (spearman, top1, grade migration)"
```

---

## Task 12: CSV → SQLite 시딩 (FastAPI TestClient 재사용)

**Files:**
- Create: `graphDB/experiment/seeding.py`
- Test: `graphDB/tests/experiment/test_seeding_integration.py`

**Interfaces:**
- Produces: `seed_sqlite(db_path: str, repo_root: str) -> Session` — 그룹 CSV들을 `backend/routers/admin_upload_grouped`의 엔드포인트에 TestClient로 POST해 적재하고 세션 반환. 순서: org → courses → curriculum → requirements → students → enrollments.

**구현 노트(중요):** `backend`는 `DATABASE_URL`(SQLite) 환경변수로 엔진을 만든다. 시딩 전 `DATABASE_URL=sqlite:///<db_path>` 설정 후 `backend.main`의 `app`을 import, `TestClient(app)`으로 각 그룹 CSV를 업로드. 각 응답의 성공 카운트를 assert. 실제 CSV 컬럼이 엔드포인트 기대와 어긋나면 이 태스크에서 드러난다 → 매핑 조정.

- [ ] **Step 1: 통합 테스트 작성** — `test_seeding_integration.py` (실 CSV 사용, 느릴 수 있음)

```python
import os, tempfile
import pytest
from experiment.seeding import seed_sqlite
from lions_core.models import Student, Course, Department

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.integration
def test_seed_loads_expected_rows():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "t.db")
        s = seed_sqlite(db, REPO)
        assert s.query(Course).count() > 500
        assert s.query(Student).count() == 300
        assert s.query(Department).count() >= 40
        s.close()
```

- [ ] **Step 2: 실패 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_seeding_integration.py -v` → FAIL

- [ ] **Step 3: 구현** — `graphDB/experiment/seeding.py`. 각 그룹 엔드포인트 경로·필드는 `backend/routers/admin_upload_grouped.py`를 참조해 실제 CSV(`group1_colleges_depts_.csv`, `group3_courses.csv`, `group4_교육과정_전체.csv`, `group5_requirements_recs.csv`, `sample_students_300.csv`, `sample_enrollments_300.csv`)를 순서대로 업로드. 골격:

```python
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def seed_sqlite(db_path: str, repo_root: str):
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    from backend.database import Base, engine  # settings가 위 env를 읽도록 import 순서 유지
    from backend.main import app
    from fastapi.testclient import TestClient
    Base.metadata.create_all(engine)
    client = TestClient(app)

    def post(route, path):
        with open(os.path.join(repo_root, path), "rb") as fh:
            r = client.post(route, files={"file": (os.path.basename(path), fh, "text/csv")})
        assert r.status_code == 200, f"{route}: {r.status_code} {r.text[:200]}"
        return r

    post("/api/admin/upload/org", "group1_colleges_depts_.csv")
    post("/api/admin/upload/courses", "group3_courses.csv")
    post("/api/admin/upload/curriculum", "group4_교육과정_전체.csv")
    post("/api/admin/upload/requirements", "group5_requirements_recs.csv")
    post("/api/admin/upload/students", "sample_students_300.csv")
    post("/api/admin/upload/enrollments", "sample_enrollments_300.csv")

    return sessionmaker(bind=engine)()
```

실제 라우트 prefix·CSV 포맷은 실행 중 확인해 맞춘다. (라우트 prefix는 `backend/main.py`의 include_router에서 확인.)

- [ ] **Step 4: 통과 확인** — Run: `cd graphDB && python -m pytest tests/experiment/test_seeding_integration.py -v -m integration` → PASS. 실패 시 실제 CSV↔엔드포인트 매핑을 맞출 때까지 반복(systematic-debugging).

- [ ] **Step 5: 커밋**

```bash
git add graphDB/experiment/seeding.py graphDB/tests/experiment/test_seeding_integration.py
git commit -m "feat(experiment): CSV->SQLite seeding via grouped upload"
```

---

## Task 13: RQ2 오케스트레이터 (CLI, 12,000건 재계산 + 영향 분석)

**Files:**
- Create: `graphDB/experiment_rq2.py`
- Test: 수동 검증 (시딩+평가 필요)

**Interfaces:**
- Consumes: Task 9–12 전체 + `experiment.pairs.compute_hybrid_similarity`.
- Produces: `graphDB/results/rq2/` 산출물.

- [ ] **Step 1: 오케스트레이터 작성** — `graphDB/experiment_rq2.py`:

```python
"""RQ2: 임계값 변화의 하위 시스템 영향 (오프라인 전면 재계산)."""
from __future__ import annotations
import argparse, os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lions_core.models import Student, Department
from lions_core.constants import LIONS_COLLEGE_ID
from similarity_engine import load_course_data
from experiment.pairs import compute_hybrid_similarity
from experiment.similarity_lookup import build_lookup, make_similarity_fn
from experiment.injected_eval import InjectedEvaluationService
from experiment.seeding import seed_sqlite
from experiment.impact_metrics import spearman_vs_baseline, top1_change_rate, grade_migration


def _evaluate_all(db, sim_fn, threshold):
    svc = InjectedEvaluationService(db, sim_fn, threshold)
    students = [s.student_id for s in db.query(Student).all()]
    depts = [d.id for d in db.query(Department).all() if d.id > LIONS_COLLEGE_ID]
    rows = []
    for did in depts:
        results = svc.batch_evaluate_students([str(s) for s in students], did)
        for r in results:
            rows.append({"student_id": r["student_id"], "department_id": did,
                         "overall_score": r["overall_score"], "grade": r["grade"]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--csv", default="course_all_aggregated.csv")
    ap.add_argument("--out", default="results/rq2")
    ap.add_argument("--tstar", type=float, required=True, help="RQ1에서 얻은 t*")
    ap.add_argument("--db", default="results/rq2/seed.db")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    df = load_course_data(args.csv)
    sim = compute_hybrid_similarity(df)
    lut = build_lookup(df, sim, min_keep=0.6)
    sim_fn = make_similarity_fn(lut)

    db = seed_sqlite(args.db, args.repo_root)

    thresholds = sorted({0.6, 0.7, 0.8, round(args.tstar, 2)})
    evals = {}
    for t in thresholds:
        e = _evaluate_all(db, sim_fn, t)
        e.to_csv(f"{args.out}/evaluations_{t}.csv", index=False)
        evals[t] = e

    base = evals[0.8]  # 현행 실효값 기준선
    summary = {"thresholds": thresholds, "n_additional_relations": {}}
    for t in thresholds:
        summary["n_additional_relations"][t] = int(sum(
            1 for v in lut.values() if v >= t) )
    stab_rows = []
    for t in thresholds:
        rho = spearman_vs_baseline(evals[t], base)
        stab_rows.append({"threshold": t,
                          "spearman_mean": float(rho.mean()) if len(rho) else 1.0,
                          "spearman_min": float(rho.min()) if len(rho) else 1.0,
                          "top1_change_rate": top1_change_rate(evals[t], base)})
        grade_migration(evals[t], base).to_csv(f"{args.out}/grade_migration_{t}.csv")
    pd.DataFrame(stab_rows).to_csv(f"{args.out}/ranking_stability.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    for t in thresholds:
        ax.hist(evals[t]["overall_score"], bins=40, histtype="step", label=f"t={t}")
    ax.set_xlabel("overall_score"); ax.set_ylabel("빈도"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(f"{args.out}/score_shift.png", dpi=150); plt.close(fig)

    json.dump(summary, open(f"{args.out}/summary.json", "w"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 소규모 스모크 실행** — 임의 t*로 파이프라인 검증:

Run: `cd graphDB && python experiment_rq2.py --tstar 0.75`
Expected: `results/rq2/`에 `evaluations_{0.6,0.7,0.75,0.8}.csv`(각 12,000행 = 학생 300 × 학과 40), `ranking_stability.csv`, `grade_migration_*.csv`, `score_shift.png`, `summary.json` 생성. `ranking_stability`의 t=0.8 행은 ρ=1.0·top1=0.0(기준선 자기자신).

- [ ] **Step 3: 산출물 확인** — Run: `cd graphDB && cat results/rq2/ranking_stability.csv results/rq2/summary.json`. 임계값이 낮아질수록 `n_additional_relations` 증가·top1_change_rate 증가 경향 확인.

- [ ] **Step 4: 커밋**

```bash
git add graphDB/experiment_rq2.py graphDB/results/rq2/
git commit -m "feat(experiment): RQ2 orchestrator (threshold impact recompute)"
```

- [ ] **Step 5: 최종 실행** — RQ1의 실제 `tstar_llm`으로 재실행:
Run: `cd graphDB && python experiment_rq2.py --tstar <RQ1_tstar_llm>`

---

## Task 14: 전체 테스트 + 문서 요약

**Files:**
- Modify: `graphDB/README.md` (실험 실행법 섹션 추가)
- Create: `graphDB/results/README.md` (산출물 해설)

- [ ] **Step 1: 전체 유닛 테스트** — Run: `cd graphDB && python -m pytest tests/experiment -v -m "not integration"` → 전부 PASS
- [ ] **Step 2: README에 실행법 추가** — RQ1/RQ2 CLI 사용법, `--no-llm` 옵션, `t*` 전달 흐름, OpenAI 키 필요 사항 명시.
- [ ] **Step 3: 산출물 해설 작성** — `graphDB/results/README.md`에 각 CSV/PNG 의미 1줄씩.
- [ ] **Step 4: 커밋**

```bash
git add graphDB/README.md graphDB/results/README.md
git commit -m "docs(experiment): RQ1/RQ2 usage and artifact guide"
```

---

## Self-Review

**Spec coverage:**
- RQ1 유사도=하이브리드 → Task 1. 층화표본 400쌍+N_k → Task 2. 블라인드 채점표 → Task 8. LLM 골드(2회+κ) → Task 7,8. TF-IDF silver → Task 6. GT 비교 κ → Task 5,8. 가중 P/R/F1 스윕+PR-AUC+t* → Task 3,8. 부트스트랩 CI → Task 4,8. ✅
- RQ2 SQLite 시딩 → Task 12. 유사도 사전계산 → Task 9. 주입 재계산 → Task 10,13. {0.6,0.7,0.8,t*} → Task 13. Spearman ρ·Top-1·등급이동·점수분포·추가관계수 → Task 11,13. ✅
- 방법론 한계 서술 → Task 14 README + 스펙 §7. ✅

**Placeholder scan:** 코드 스텝은 모두 실제 코드. Task 12는 실 CSV↔엔드포인트 매핑을 실행 중 확정해야 하는 유일한 지점 — 통합 테스트가 이를 강제. 그 외 placeholder 없음.

**Type consistency:** `SampledPair`(pair_id,i,j,sim,bin_idx,weight)를 Task 1 정의 후 2·3·4·6·7에서 동일 사용. 레이블은 전부 `dict[pair_id,int]`. `sweep`/`best_threshold`/`pr_auc` 시그니처 Task 3↔4↔8 일치. `make_similarity_fn`/`InjectedEvaluationService` 시그니처 Task 9↔10↔13 일치. ✅
