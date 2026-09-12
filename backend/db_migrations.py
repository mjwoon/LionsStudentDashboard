"""앱 시작 시 DB 스키마 준비.

Render 무료 플랜은 `preDeployCommand`(`alembic upgrade head`)를 실행하지 않는다.
따라서 운영(APP_ENV=production)에서는 앱 시작 시 Alembic 마이그레이션을 직접 적용한다.
개발/테스트에서는 기존처럼 create_all(lions_core.init_db)을 사용한다.

두 경로 모두 동일한 Base.metadata 에서 파생되므로 스키마 결과는 일치한다.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from lions_core.constants import DUMMY_DATA_MARKER
from lions_core.db import SessionLocal, engine, init_db

logger = logging.getLogger("uvicorn.error")

_BACKEND_DIR = Path(__file__).resolve().parent

# create_all 로 먼저 생성돼 alembic 이력(alembic_version)이 없는 기존 운영 DB를
# 채택(adopt)할 baseline 리비전. grade NOT NULL 상태, 즉 d4e8f1a2b3c9('grade nullable')
# 적용 직전에 해당한다. 이후엔 alembic_version 이 생기므로 이 분기는 다시 타지 않는다.
_LEGACY_BASELINE = "ec5677acf896"


def _alembic_config():
    """프로그램적 실행용 Alembic Config.

    ini 파일 경로를 넘기지 않는다 → env.py 의 `fileConfig`(logging 재설정)를 건너뛰어
    uvicorn 로거를 덮어쓰지 않는다. sqlalchemy.url 은 env.py 가 앱 settings 에서 직접
    설정하므로 여기서 지정할 필요가 없다.
    """
    from alembic.config import Config

    cfg = Config()
    # 실행 CWD 에 의존하지 않도록 스크립트 위치를 절대경로로 고정한다.
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "migrations"))
    return cfg


def _upgrade_via_alembic() -> None:
    from alembic import command
    from sqlalchemy import inspect

    tables = set(inspect(engine).get_table_names())
    cfg = _alembic_config()

    # create_all 로 만들어졌지만 alembic 이력이 없는 기존 DB는 최초 1회 baseline 으로 stamp.
    # (stamp 없이 upgrade 하면 초기 마이그레이션의 create_table 이 "이미 존재" 에러를 낸다.)
    if "alembic_version" not in tables and "student_courses" in tables:
        logger.info("Alembic 이력 없는 기존 스키마 감지 → baseline(%s) stamp", _LEGACY_BASELINE)
        command.stamp(cfg, _LEGACY_BASELINE)

    logger.info("Alembic upgrade → head")
    command.upgrade(cfg, "head")


def init_schema() -> None:
    """실 DB(PostgreSQL)는 Alembic 마이그레이션, 그 외(SQLite 등 개발/테스트)는 create_all.

    APP_ENV 같은 환경변수가 (대시보드 관리형 서비스 등에서) 누락돼도 안전하도록
    DB 방언을 기준으로 판단한다. Postgres = 실제 배포 DB = 마이그레이션 대상.
    """
    dialect = engine.dialect.name
    logger.info("init_schema: dialect=%s APP_ENV=%s", dialect, os.getenv("APP_ENV") or "(unset)")
    if dialect == "postgresql":
        _upgrade_via_alembic()
    else:
        init_db()

    warn_if_dummy_requirements_present()


def count_dummy_requirements(db) -> int:
    """DB에 남아 있는 합성(더미) 진입요건 수.

    생성 데이터와 원본이 같은 CSV에 병합돼 있고 requirement_text는 API 응답에도
    화면에도 실리지 않으므로, DB를 직접 들여다보는 것 말고는 알 방법이 없다.
    """
    from models.models import DepartmentEntryRequirement

    return (
        db.query(DepartmentEntryRequirement)
        .filter(DepartmentEntryRequirement.requirement_text.like(f"{DUMMY_DATA_MARKER}%"))
        .count()
    )


def warn_if_dummy_requirements_present() -> None:
    """운영에 합성 요건이 들어가 있으면 기동 로그에 크게 남긴다.

    기동을 거부하지는 않는다. 데이터 상태 때문에 서비스를 통째로 내리는 것은
    과하고, 이 상황은 사람이 데이터를 바로잡아야 풀리기 때문이다. 대신 놓칠 수
    없게 ERROR로 남긴다 — 학생이 존재하지 않는 요건을 '충족'으로 보고 진로를
    정하는 것이 이 문제의 실제 피해다.
    """
    if (os.getenv("APP_ENV") or "").lower() != "production":
        return

    try:
        with SessionLocal() as db:
            count = count_dummy_requirements(db)
    except Exception as exc:  # 탐지 실패가 기동을 막아서는 안 된다
        logger.warning("더미 데이터 점검을 건너뜀: %s", exc)
        return

    if count:
        logger.error(
            "운영 DB에 합성(더미) 진입요건 %d건이 있습니다. "
            "scripts/generate_dummy_requirements.py가 만든 데이터이며 실제 학사 규정이 "
            "아닙니다. 학생에게 존재하지 않는 요건이 '충족'으로 표시됩니다. "
            "requirement_text가 '%s'로 시작하는 행을 제거하고 실제 규정으로 교체하세요.",
            count,
            DUMMY_DATA_MARKER,
        )
