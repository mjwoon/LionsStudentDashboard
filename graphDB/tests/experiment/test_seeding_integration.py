"""실 CSV 시딩 스모크 (루트 3.12 환경, fastapi 필요). 느릴 수 있음."""
import os
import tempfile

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("lions_core")

# .../graphDB/tests/experiment/<file> → 4단계 상위가 리포 루트
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.integration
def test_seed_loads_expected_rows():
    from experiment.seeding import seed_sqlite
    from lions_core.models import Student, Course, Department

    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "t.db")
        s = seed_sqlite(db, REPO)
        # DB Course 는 group3(고유 318)에서 온다. course_all_aggregated(1493)는 유사도 전용.
        assert s.query(Course).count() >= 300
        assert s.query(Student).count() == 300
        assert s.query(Department).count() >= 40
        s.close()
