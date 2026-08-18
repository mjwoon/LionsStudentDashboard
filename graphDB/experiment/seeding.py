"""CSV → 로컬 SQLite 시딩 (backend 그룹 업로드 엔드포인트를 TestClient로 재사용).

루트 3.12 환경 전용(fastapi + backend + lions_core 필요). RQ2 오프라인 재계산의
DB를 실제 업로드·검증 경로로 채운다.
"""
from __future__ import annotations

import os

# 엔진은 lions_core.db 가 import 시점에 settings(DATABASE_URL)로 생성한다.
# 따라서 어떤 backend 모듈보다 먼저 DATABASE_URL 을 지정해야 한다.
_UPLOADS = [
    ("/api/admin/upload-grouped/org", "group1_colleges_depts_.csv"),
    ("/api/admin/upload-grouped/courses", "group3_courses.csv"),
    ("/api/admin/upload-grouped/curriculum", "group4_교육과정_전체.csv"),
    ("/api/admin/upload-grouped/requirements", "group5_requirements_recs.csv"),
    ("/api/admin/upload-grouped/students", "sample_students_300.csv"),
    ("/api/admin/upload-grouped/enrollments", "sample_enrollments_300.csv"),
]


def seed_sqlite(db_path: str, repo_root: str):
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from fastapi.testclient import TestClient
    import main  # backend/main.py (sys.path 에 backend 필요)
    from lions_core.db import SessionLocal, engine, init_db

    init_db()  # create_all (sqlite)

    with TestClient(main.app) as client:  # lifespan 실행(init_schema)
        for route, fname in _UPLOADS:
            path = os.path.join(repo_root, fname)
            with open(path, "rb") as fh:
                resp = client.post(route, files={"file": (fname, fh, "text/csv")})
            assert resp.status_code == 200, f"{route}: {resp.status_code} {resp.text[:300]}"

    return SessionLocal(bind=engine)
