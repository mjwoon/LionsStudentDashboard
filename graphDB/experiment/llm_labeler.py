"""OpenAI(gpt-4o) 이진 대체 인정 레이블러. client 주입 → 테스트는 fake 사용."""
from __future__ import annotations

import re
import time

import numpy as np


def _is_rate_limit(e: Exception) -> bool:
    return type(e).__name__ == "RateLimitError" or getattr(e, "status_code", None) == 429


def _create_with_retry(client, model, prompt, max_retries=8, retry_base_s=1.0):
    """429(TPM/RPM) 시 지수 백오프 재시도. 다른 예외는 즉시 전파."""
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
        except Exception as e:  # noqa: BLE001
            if _is_rate_limit(e) and attempt < max_retries:
                time.sleep(min(retry_base_s * (2 ** attempt), 30.0))
                continue
            raise


def build_prompt(a_name, a_desc, b_name, b_desc) -> str:
    return (
        "너는 대학 학사 담당자다. 학생이 아래 '이수 과목'을 들었을 때, "
        "'대상 과목'을 대체 인정(같은 과목으로 인정)할 수 있는지 판단하라.\n"
        "과목명과 개요만 근거로 삼고, 오직 '예' 또는 '아니오' 한 단어로만 답하라.\n\n"
        f"[이수 과목] 이름: {a_name}\n개요: {a_desc}\n\n"
        f"[대상 과목] 이름: {b_name}\n개요: {b_desc}\n\n답:"
    )


def parse_decision(text: str) -> int:
    """응답 → 1/0. 긍정 신호가 있고 부정 신호가 없을 때만 1."""
    t = (text or "").strip().lower()
    positive = re.search(r"(예|네|가능|인정|yes|^1\b|^1$)", t)
    negative = re.search(r"(아니|불가|불인정|no)", t)
    return 1 if (positive and not negative) else 0


def label_pairs(
    df,
    sample,
    client,
    model: str = "gpt-4o",
    seed: int = 42,
    throttle_s: float = 0.7,
    max_retries: int = 8,
    retry_base_s: float = 1.0,
):
    """각 쌍을 이진 판정. TPM 한도 회피용 호출 간 스로틀(throttle_s)과 429 재시도 포함."""
    rng = np.random.default_rng(seed)
    names = df["교과목 이름"].fillna("").tolist()
    descs = df["교과목개요"].fillna("").tolist()
    labels = {}
    for sp in sample:
        i, j = sp.i, sp.j
        if rng.random() < 0.5:  # 제시 순서 무작위화 (앵커링 차단)
            i, j = j, i
        prompt = build_prompt(names[i], descs[i], names[j], descs[j])
        resp = _create_with_retry(client, model, prompt, max_retries, retry_base_s)
        labels[sp.pair_id] = parse_decision(resp.choices[0].message.content)
        if throttle_s:
            time.sleep(throttle_s)
    return labels
