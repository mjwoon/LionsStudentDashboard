"""timestamps to timezone-aware

기존 naive TIMESTAMP 컬럼을 TIMESTAMPTZ로 변환한다. 저장된 값은 UTC 기준이었으므로
`AT TIME ZONE 'UTC'`로 해석해 변환한다. (Postgres 전용; 그 외 방언에서는 no-op —
SQLite는 create_all이 이미 tz-aware로 생성)

Revision ID: ec5677acf896
Revises: b21d8a64fbb7
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ec5677acf896"
down_revision: Union[str, Sequence[str], None] = "b21d8a64fbb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column) 타임스탬프 컬럼 목록
_COLUMNS = [
    ("students", "updated_at"),
    ("courses", "created_at"),
    ("student_courses", "created_at"),
    ("survey_rounds", "start_date"),
    ("survey_rounds", "end_date"),
    ("major_surveys", "survey_date"),
    ("student_requirement_status", "calculated_at"),
]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, col in _COLUMNS:
        op.alter_column(
            table,
            col,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, col in _COLUMNS:
        op.alter_column(
            table,
            col,
            type_=sa.DateTime(),
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )
