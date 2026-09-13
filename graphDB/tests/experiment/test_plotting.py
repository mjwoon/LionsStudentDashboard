"""한글 폰트 등록 헬퍼."""
import matplotlib
import pytest

from experiment import plotting
from experiment.plotting import available_korean_fonts, use_korean_font, CANDIDATES


@pytest.fixture(autouse=True)
def _restore_font_state():
    """폰트 캐시와 rcParams 를 매 테스트 후 되돌린다.

    캐시를 남기면 이 파일의 monkeypatch 테스트가 다른 파일의 그림 테스트까지
    '한글 폰트 없음' 상태로 오염시킨다.
    """
    saved = (plotting._applied, plotting._checked,
             matplotlib.rcParams["font.family"],
             matplotlib.rcParams["axes.unicode_minus"])
    yield
    (plotting._applied, plotting._checked,
     matplotlib.rcParams["font.family"],
     matplotlib.rcParams["axes.unicode_minus"]) = saved


def test_available_fonts_are_from_candidates_and_ordered():
    found = available_korean_fonts()
    assert set(found) <= set(CANDIDATES)
    order = {n: i for i, n in enumerate(CANDIDATES)}
    assert found == sorted(found, key=lambda n: order[n]), "우선순위 순이어야 한다"


def test_use_korean_font_sets_rcparams_when_available(monkeypatch):
    monkeypatch.setattr(plotting, "available_korean_fonts", lambda: ["NanumGothic"])
    name = use_korean_font(force=True)
    assert name == "NanumGothic"
    assert "NanumGothic" in matplotlib.rcParams["font.family"]
    # 한글 폰트 전환 시 유니코드 마이너스는 꺼야 한다
    assert matplotlib.rcParams["axes.unicode_minus"] is False


def test_use_korean_font_warns_and_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr(plotting, "available_korean_fonts", lambda: [])
    with pytest.warns(RuntimeWarning, match="한글 폰트"):
        assert use_korean_font(force=True) is None


def test_real_environment_has_a_korean_font():
    """이 저장소의 그림은 한글 라벨을 쓰므로 실행 환경에 폰트가 있어야 한다."""
    assert available_korean_fonts(), (
        "한글 폰트 없음 — 그림의 한글이 깨진다. "
        "macOS 는 기본 제공, 리눅스는 fonts-nanum 설치 필요."
    )


def test_cache_makes_repeat_calls_idempotent(monkeypatch):
    calls = []
    real = plotting.available_korean_fonts
    monkeypatch.setattr(plotting, "available_korean_fonts",
                        lambda: (calls.append(1), real())[1])
    use_korean_font(force=True)
    use_korean_font()
    use_korean_font()
    assert len(calls) == 1, "캐시 이후에는 폰트를 다시 탐색하지 않아야 한다"
