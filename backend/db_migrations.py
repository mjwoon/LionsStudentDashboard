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

from lions_core.db import engine, init_db

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
    """운영은 Alembic 마이그레이션, 개발/테스트는 create_all 로 스키마를 준비한다."""
    if os.getenv("APP_ENV", "").lower() == "production":
        _upgrade_via_alembic()
    else:
        init_db()
