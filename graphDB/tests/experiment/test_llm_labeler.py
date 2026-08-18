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
                class M:
                    content = "예"

                class C:
                    message = M()

                class R:
                    choices = [C()]

                return R()


def test_label_pairs_uses_client_and_covers_all():
    df = pd.DataFrame({"교과목 이름": ["A", "B"], "교과목개요": ["x", "y"]})
    sample = [SampledPair(0, 0, 1, 0.8, 4, 1.0)]
    labels = label_pairs(df, sample, client=FakeClient(), model="gpt-4o", seed=1, throttle_s=0)
    assert labels == {0: 1}


class FlakyClient:
    """첫 호출은 429(rate limit) 후 성공. 재시도 검증용."""

    def __init__(self, fail_times=1):
        self.fail_times = fail_times
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kw):
        self.calls += 1
        if self.calls <= self.fail_times:
            e = Exception("rate limit")
            e.status_code = 429
            raise e

        class M:
            content = "예"

        class C:
            message = M()

        class R:
            choices = [C()]

        return R()


def test_label_pairs_retries_on_rate_limit():
    df = pd.DataFrame({"교과목 이름": ["A", "B"], "교과목개요": ["x", "y"]})
    sample = [SampledPair(0, 0, 1, 0.8, 4, 1.0)]
    client = FlakyClient(fail_times=2)
    labels = label_pairs(df, sample, client=client, seed=1, throttle_s=0, retry_base_s=0)
    assert labels == {0: 1}
    assert client.calls == 3  # 2회 실패 후 성공
