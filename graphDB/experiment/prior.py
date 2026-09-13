r"""하위 구간 양성 수(M)에 대한 검정력과 재현율 민감도.

RQ1 의 재현율은 **"유사도 0.6 미만에는 대체 인정 가능한 쌍이 없다"는 전제** 위에
서 있다. 하위 두 층에서 양성이 0건 관측됐기 때문인데, 0/160 이 보장하는 범위는
생각보다 훨씬 좁다.

**용어를 정확히 할 것.** 이것은 식별(identifiability) 문제가 아니라 검정력 문제다.
표본추출 확률이 층마다 정확히 알려져 있고 모든 쌍의 선택 확률이 0보다 크므로,
하위 구간 양성 수의 Horvitz–Thompson 추정량은 존재하고 불편이며 그 값은 0이다.
양성-미표지(PU) 학습에서 말하는 클래스 사전확률의 비식별성 — 기약성(irreducibility)
가정 없이는 사전확률이 식별되지 않는다는 결과 — 은 표집확률을 모르고 음성
레이블도 없는 상황의 이야기이고, 본 설계에는 해당하지 않는다. 여기서 문제는
**추정량이 없다는 것이 아니라 분산이 감당할 수 없이 크다는 것**이다
(모집단 110만에서 표본 100).

그래서 이 모듈은 전제를 더 그럴듯한 전제로 바꾸려 하지 않는다. 대신
**관측이 M 을 얼마나 제약하는지를 그대로 보여준다.** 하위 양성 수 M 을 가정했을 때

  - 우리가 실제로 본 결과(0/100, 0/60)가 나올 확률
  - 그때의 재현율

를 함께 제시하면, 넓은 구간에 걸쳐 재현율이 데이터가 아니라 전제에 의해 결정된다는
사실이 수치로 드러난다.

부수적으로 이 계산은 계획서가 쓴 rule of three 보다 경계를 좁힌다. rule of three 는
층마다 따로 상한을 잡아 더하지만(보수적), 여기서는 두 층에서 **동시에** 0건이 나올
결합 확률을 초기하분포로 정확히 계산한다(비복원 표집이므로 이항 근사도 쓰지 않는다).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def prob_zero_in_stratum(N: int, n: int, M: float) -> float:
    """모집단 N 중 양성이 M 개일 때, 비복원 n 개 표본에 하나도 안 들어올 확률.

    초기하 P(X=0) = C(N-M, n) / C(N, n) = prod_{i<n} (N-M-i)/(N-i).
    M 은 연속값을 허용한다(가정 격자를 매끄럽게 훑기 위해).
    """
    if M <= 0:
        return 1.0
    if M >= N - n + 1:
        return 0.0
    i = np.arange(n)
    terms = (N - M - i) / (N - i)
    if np.any(terms <= 0):
        return 0.0
    return float(np.exp(np.sum(np.log(terms))))


def observation_probability(strata, M: float) -> float:
    """가정한 M 을 층 크기 비례로 배분했을 때 모든 층에서 0건이 나올 확률.

    strata: [(N_k, n_k), ...] — 양성이 0건 관측된 층들.
    """
    total_N = sum(N for N, _ in strata)
    if total_N <= 0:
        return 1.0
    p = 1.0
    for N, n in strata:
        p *= prob_zero_in_stratum(N, n, M * N / total_N)
    return p


def max_consistent_M(strata, alpha: float = 0.05, hi: float = 1e7) -> float:
    """유의수준 alpha 에서 기각되지 않는 최대 M (이분 탐색).

    이보다 큰 M 이면 두 층에서 동시에 0건이 나올 확률이 alpha 미만이 된다.
    즉 데이터가 배제할 수 있는 것은 이 값 위쪽뿐이고, 아래쪽은 전부 관측과
    양립한다 — 재현율이 그 구간 전체에서 전제에 의해 정해진다는 뜻이다.
    """
    if observation_probability(strata, 0.0) < alpha:
        return 0.0
    lo, hi = 0.0, float(hi)
    for _ in range(200):
        mid = (lo + hi) / 2
        if observation_probability(strata, mid) >= alpha:
            lo = mid
        else:
            hi = mid
    return lo


def recall_under_hypothesis(tp: float, positives_measured: float, M: float) -> float:
    """하위 구간에 양성이 M 개 더 있다고 가정했을 때의 재현율.

    분자(TP)는 그대로다 — 임계값 위에서 잡은 양성은 가정과 무관하다.
    분모만 커지므로 재현율은 M 에 대해 단조 감소한다.
    """
    denom = positives_measured + M
    return float(tp / denom) if denom > 0 else 0.0


def sensitivity_table(strata, tp: float, positives_measured: float,
                      grid=None, alpha: float = 0.05) -> pd.DataFrame:
    """M 격자별 관측 확률과 재현율."""
    if grid is None:
        grid = [0, 10, 100, 500, 1_000, 5_000, 10_000, 33_000, 50_000]
    rows = []
    for M in grid:
        p = observation_probability(strata, float(M))
        rows.append({
            "M": float(M),
            "p_observe_zero": p,
            "rejected_at_alpha": bool(p < alpha),
            "recall": recall_under_hypothesis(tp, positives_measured, float(M)),
        })
    return pd.DataFrame(rows)


def name_collision_candidates(names, pairs, sims, max_sim: float = 0.6):
    """유사도는 낮은데 교과목명이 완전히 같은 쌍.

    무작위 표본은 하위 구간의 양성을 찾아내기에 비효율적이다(모집단 110만에 표본
    100). 대신 **유사도가 놓쳤을 가능성이 가장 큰 곳**을 직접 뒤진다. 이름이
    똑같은데 하이브리드 유사도가 낮다면 유사도 척도의 실패 사례이므로,
    그런 쌍이 없다는 것은 무작위 0건보다 훨씬 강한 증거다.

    반환: [(i, j, sim), ...]
    """
    out = []
    for (i, j), s in zip(pairs, sims):
        if s >= max_sim:
            continue
        a, b = str(names[i]).strip(), str(names[j]).strip()
        if a and a == b:
            out.append((int(i), int(j), float(s)))
    return out
