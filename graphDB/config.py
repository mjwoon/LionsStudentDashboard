"""
graphDB 빌드 파이프라인 설정 (단일 출처).

env 변수에서 Neo4j 자격증명·CSV 경로·임계값·하이브리드 가중치·모델명을 읽는다.
그동안 파일마다 제각각이던 기본값(비밀번호 password / password123 / your_password,
유사도 임계값 0.5 / 0.6 / 0.7)의 드리프트를 이 한 곳으로 수렴시킨다.

graphDB 는 ADR 0001에 따라 lions-core workspace 멤버가 아니므로 lions_core.config 를
import 하지 않고 자체 Settings 를 갖는다(설계상 인정된 경계).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from text_features import PRODUCTION_MODEL_NAME


def load_dotenv(paths: tuple[str, ...] = (".env", "../.env")) -> None:
    """현재/상위 디렉토리의 .env 를 찾아 환경변수로 로드(기존 값은 유지)."""
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))
        break


@dataclass(frozen=True)
class Settings:
    """graphDB 빌드에 필요한 모든 설정의 단일 표현."""

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    csv_path: str
    similarity_threshold: float
    prereq_threshold: float
    hybrid_weight: float
    model_name: str

    @classmethod
    def from_env(cls, *, use_dotenv: bool = True) -> "Settings":
        """
        환경변수에서 설정을 구성한다.

        기본값은 '현재 프로덕션 진입점(quick_start.py)의 동작'을 그대로 보존한다:
        유사도 임계값 0.5, 선수강 임계값 0.6, 하이브리드 가중치 0.7.
        """
        if use_dotenv:
            load_dotenv()
        return cls(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=(os.environ.get("NEO4J_USER")
                        or os.environ.get("NEO4J_USERNAME")
                        or "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "password123"),
            csv_path=os.environ.get("GRAPHDB_CSV_PATH", "course_all_aggregated.csv"),
            similarity_threshold=float(os.environ.get("GRAPHDB_SIM_THRESHOLD", "0.5")),
            prereq_threshold=float(os.environ.get("GRAPHDB_PREREQ_THRESHOLD", "0.6")),
            hybrid_weight=float(os.environ.get("GRAPHDB_HYBRID_WEIGHT", "0.7")),
            model_name=os.environ.get("GRAPHDB_MODEL_NAME", PRODUCTION_MODEL_NAME),
        )
