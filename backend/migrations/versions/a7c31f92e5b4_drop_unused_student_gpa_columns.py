"""drop students.current_gpa / students.total_credits

두 컬럼은 앱이 한 번도 채우지 않는다. 값을 쓰던 유일한 코드(update_student_gpa)는
호출자가 없어 제거됐고, 읽던 유일한 코드(routers/dashboard.py의 통계 블록)는 같은
경로를 선언한 surveys.py에 가려 실행되지 않아 함께 제거됐다.

현재 저장소에서 이 두 컬럼을 참조하는 곳은 없다. 스키마에서도 뺀다.

되돌릴 수 있는 범위: downgrade는 컬럼을 다시 만들지만 값은 복원하지 못한다
(원래 채우는 코드가 없으므로 복원할 값도 없다).

Revision ID: a7c31f92e5b4
Revises: d4e8f1a2b3c9
Create Date: 2026-09-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7c31f92e5b4"
down_revision: Union[str, Sequence[str], None] = "d4e8f1a2b3c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("students", "current_gpa")
    op.drop_column("students", "total_credits")


def downgrade() -> None:
    # 값은 복원하지 않는다 — 애초에 채우는 코드가 없었다.
    op.add_column("students", sa.Column("total_credits", sa.Integer(), nullable=True))
    op.add_column("students", sa.Column("current_gpa", sa.Numeric(precision=3, scale=2), nullable=True))
