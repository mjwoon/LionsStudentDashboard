"""합성(생성) 요건 데이터 식별.

왜 텍스트로 판별할 수 없는가
---------------------------
scripts/generate_dummy_requirements.py는 실제 ELEC 규정의 관용구를 **그대로**
복제한다. 생성 텍스트와 실제 규정이 글자 단위로 같다:

    생성: "아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수"
    ELEC: "아래 5개 과목 중 성적 B(3.0) 이상 2과목 또는 A(4.0) 이상 1과목 필수"

따라서 requirement_text를 보는 어떤 판별식도 진짜 학사 규정을 오탐한다. #12의
'[더미]' 접두어는 이 문제를 접두어로 우회한 것이었고, 데이터에 그 단어를 남기지
않기로 하면서(#16) 사라졌다.

무엇으로 판별하는가
------------------
`.generated-requirements.json` 대장이다. 생성기는 **원본에 해당 항목이 없는 학과에만**
생성하므로(generate_dummy_requirements.main의 has_requirement/has_recommendation 분기),
학과코드와 행 종류만으로 실제 규정과 생성분이 겹치지 않게 나뉜다. 현재 데이터 기준
실제 요건 보유 4개 학과와 생성 대상 34개 학과의 교집합은 공집합이다.

대장은 저장소에 커밋돼 백엔드와 함께 배포되므로, CSV에 표식이 없어도 서버가
판별할 수 있다 — #16이 "대장이 CSV를 따라가지 않는다"고 남겨둔 구멍이 이 지점이다.

한계
----
학교가 나중에 생성 대상 학과(예: ACTU)의 **진짜** 규정을 주면 이 가드가 그것을
막는다. 그때는 대장에서 해당 학과코드를 빼야 한다. 오탐이 조용히 지나가는 것보다
낫다고 보고 택한 설계이며, 차단 메시지에 그 조치를 적어 둔다.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable, Mapping

logger = logging.getLogger("uvicorn.error")

# packages/lions-core/lions_core/generated_data.py -> 저장소 루트
_REPO_ROOT = Path(__file__).resolve().parents[3]

MANIFEST_ENV_VAR = "GENERATED_REQUIREMENTS_MANIFEST"
DEFAULT_MANIFEST_PATH = _REPO_ROOT / ".generated-requirements.json"

# group5 CSV에서 학과코드가 실릴 수 있는 컬럼명(업로드 라우터가 받아들이는 별칭들과 동일).
_DEPT_CODE_KEYS = ("department_code", "dept_code", "학과코드", "소속학과", "학과")
_REQUIREMENT_GROUP_KEYS = ("requirement_group", "요건그룹", "그룹")
_RECOMMENDED_COURSE_KEYS = ("recommended_course", "권장과목", "추천과목")


def manifest_path() -> Path:
    """대장 파일 경로. 배포 형태가 달라도 환경변수로 덮어쓸 수 있다."""
    override = os.getenv(MANIFEST_ENV_VAR)
    return Path(override) if override else DEFAULT_MANIFEST_PATH


class GeneratedDataManifest:
    """어느 학과에 합성 요건·권장과목을 생성했는지."""

    def __init__(self, requirement_dept_codes: Iterable[str], recommendation_dept_codes: Iterable[str]):
        self.requirement_dept_codes = frozenset(requirement_dept_codes)
        self.recommendation_dept_codes = frozenset(recommendation_dept_codes)

    @property
    def is_empty(self) -> bool:
        return not (self.requirement_dept_codes or self.recommendation_dept_codes)

    @property
    def all_dept_codes(self) -> frozenset:
        return self.requirement_dept_codes | self.recommendation_dept_codes

    def covers_row(self, row: Mapping) -> bool:
        """group5 CSV 한 행이 생성분인가.

        학과코드가 대장에 있고 **행 종류까지 맞아야** 한다. 같은 학과가 요건은
        생성분이고 권장과목은 실제일 수 있기 때문이다.
        """
        dept_code = _first_value(row, _DEPT_CODE_KEYS)
        if not dept_code:
            return False
        if _first_value(row, _REQUIREMENT_GROUP_KEYS) and dept_code in self.requirement_dept_codes:
            return True
        if _first_value(row, _RECOMMENDED_COURSE_KEYS) and dept_code in self.recommendation_dept_codes:
            return True
        return False


def _first_value(row: Mapping, keys: Iterable[str]):
    """행에서 별칭 중 처음으로 값이 있는 컬럼의 값(공백 제거)."""
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def load_manifest(path: Path | None = None) -> GeneratedDataManifest:
    """대장을 읽는다. 없거나 깨졌으면 빈 대장 — 다만 조용히 넘기지 않는다.

    #16의 교훈: 지키는 척만 하는 코드는 없는 것보다 나쁘다. 판별 근거가 없으면
    '가드가 아무것도 막지 못하는 상태'임을 로그로 드러낸다.
    """
    path = path or manifest_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning(
            "생성 데이터 대장(%s)이 없어 합성 요건을 판별할 수 없습니다. "
            "업로드 차단과 기동 시 탐지가 아무것도 잡지 못합니다.",
            path,
        )
        return GeneratedDataManifest([], [])
    except (ValueError, OSError) as exc:
        logger.warning("생성 데이터 대장(%s)을 읽지 못했습니다: %s", path, exc)
        return GeneratedDataManifest([], [])

    return GeneratedDataManifest(
        raw.get("requirement_dept_codes") or [],
        raw.get("recommendation_dept_codes") or [],
    )
