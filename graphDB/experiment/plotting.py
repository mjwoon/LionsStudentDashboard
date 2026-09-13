"""그림 공통 설정 — 한글 폰트 등록.

matplotlib 기본 폰트(DejaVu Sans)에는 한글 글리프가 없어 축·범례의 한글이
두부(□)로 렌더링된다. 논문 그림이 이 문제로 한 번 어긋난 적이 있어
(저장된 그림은 정상인데 코드로 재실행하면 깨졌다) 설정을 코드에 고정한다.

`use_korean_font()` 는 실행 환경에서 사용 가능한 한글 폰트를 찾아 등록하고
그 이름을 반환한다. 없으면 None 을 반환하고 경고만 남긴다(그림은 그려진다).
"""
from __future__ import annotations

import warnings

import matplotlib
import matplotlib.font_manager as fm

# 앞에서부터 먼저 찾은 것을 쓴다. macOS → Windows → 리눅스 배포판 순.
CANDIDATES = (
    "Apple SD Gothic Neo",
    "AppleGothic",
    "Malgun Gothic",
    "NanumGothic",
    "Nanum Gothic",
    "Noto Sans CJK KR",
    "Noto Sans KR",
    "UnDotum",
)


def available_korean_fonts() -> list[str]:
    """설치된 폰트 중 CANDIDATES 에 해당하는 것들(우선순위 순)."""
    installed = {f.name for f in fm.fontManager.ttflist}
    return [name for name in CANDIDATES if name in installed]


_applied: str | None = None
_checked = False


def use_korean_font(force: bool = False) -> str | None:
    """한글 폰트를 rcParams 에 등록하고 폰트명을 반환. 없으면 None.

    멱등이다 — 처음 한 번만 폰트를 탐색하고 이후 호출은 캐시를 쓴다.
    그림을 그리는 함수마다 부담 없이 호출할 수 있다.
    """
    global _applied, _checked
    if _checked and not force:
        return _applied
    _checked = True
    found = available_korean_fonts()
    if not found:
        warnings.warn(
            "한글 폰트를 찾지 못했습니다. 그림의 한글이 깨집니다. "
            f"다음 중 하나를 설치하세요: {', '.join(CANDIDATES[:4])}",
            RuntimeWarning,
            stacklevel=2,
        )
        _applied = None
        return None
    name = found[0]
    matplotlib.rcParams["font.family"] = name
    # 한글 폰트로 바꾸면 유니코드 마이너스 글리프가 없는 경우가 많다.
    matplotlib.rcParams["axes.unicode_minus"] = False
    _applied = name
    return name
