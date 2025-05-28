"""voltage_start null-able

Revision ID: de4b58ac3df6
Revises: 74f5adfba7d1
Create Date: 2025-05-28 09:16:47.327101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de4b58ac3df6'
down_revision: Union[str, None] = '74f5adfba7d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite 不支援 ALTER COLUMN，需用 create/copy/drop/rename 方式
    op.create_table(
        'step_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('experiment_id', sa.Integer, nullable=False),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('step_type', sa.String, nullable=False),
        sa.Column('start_time', sa.DateTime, nullable=False),
        sa.Column('end_time', sa.DateTime, nullable=True),
        sa.Column('duration', sa.Float, nullable=False),
        sa.Column('voltage_start', sa.Float, nullable=True),  # 允許 NULL
        sa.Column('voltage_end', sa.Float, nullable=False),
        sa.Column('current', sa.Float, nullable=False),
        sa.Column('capacity', sa.Float, nullable=False),
        sa.Column('energy', sa.Float, nullable=False),
        sa.Column('temperature_avg', sa.Float, nullable=False),
        sa.Column('temperature_min', sa.Float, nullable=False),
        sa.Column('temperature_max', sa.Float, nullable=False),
        sa.Column('c_rate', sa.Float, nullable=False),
        sa.Column('soc_start', sa.Float, nullable=True),
        sa.Column('soc_end', sa.Float, nullable=True),
        sa.Column('data_meta', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.execute("""
        INSERT INTO step_new
        SELECT id, experiment_id, step_number, step_type, start_time, end_time, duration,
               voltage_start, voltage_end, current, capacity, energy,
               temperature_avg, temperature_min, temperature_max, c_rate,
               soc_start, soc_end, data_meta, created_at, updated_at
        FROM step
    """)
    op.drop_table('step')
    op.rename_table('step_new', 'step')


def downgrade() -> None:
    pass
