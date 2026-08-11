"""make student_courses.grade nullable

진행중(예: 2학기) 과목은 성적이 아직 없으므로 grade 컬럼을 NULL 허용으로 변경한다.
앱 로직(GPA 계산·요건 평가)은 이미 `grade IS NULL` / `grade = ''` 인 과목을 제외하므로
설계 의도와 일치한다. numeric_grade 는 이미 nullable.

Revision ID: d4e8f1a2b3c9
Revises: ec5677acf896
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e8f1a2b3c9"
down_revision: Union[str, Sequence[str], None] = "ec5677acf896"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "student_courses",
        "grade",
        existing_type=sa.String(length=5),
        nullable=True,
    )


def downgrade() -> None:
    # NOT NULL 복원 전에 NULL 값을 빈 문자열로 채운다.
    op.execute("UPDATE student_courses SET grade = '' WHERE grade IS NULL")
    op.alter_column(
        "student_courses",
        "grade",
        existing_type=sa.String(length=5),
        nullable=False,
    )
